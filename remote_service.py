#!/usr/bin/env python3
"""
Remote Unlock Service
Handles Supabase real-time subscription for remote lock commands.
Integrates with the existing Lock accessory for actual unlock operations.
"""

import os
import asyncio
import signal
import threading
import logging
from typing import Optional
from supabase import create_client, Client, AsyncClient

# Suppress verbose logging from Supabase client libraries
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("supabase").setLevel(logging.WARNING)
logging.getLogger("postgrest").setLevel(logging.WARNING)
logging.getLogger("realtime").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


class RemoteUnlockService:
    """Service that subscribes to Supabase for remote unlock commands"""
    
    def __init__(
        self,
        supabase_url: str,
        supabase_anon_key: str,
        lock_id: str = "front-door",
        lock_accessory=None
    ):
        self.supabase_url = supabase_url
        self.supabase_anon_key = supabase_anon_key
        self.lock_id = lock_id
        self.lock_accessory = lock_accessory
        
        # Initialize Supabase client for realtime
        self.supabase_realtime: AsyncClient = AsyncClient(supabase_url, supabase_anon_key)
        
        # Threading and lifecycle management
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._shutdown_event = None  # Will be created in the async context
        
        # State management
        self.is_unlocking = False
        
        log.info(f"RemoteUnlockService initialized for lock_id: {lock_id}")

    def start(self):
        """Start the remote unlock service in a separate thread"""
        if self._running:
            log.warning("RemoteUnlockService is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        log.info("RemoteUnlockService started")

    def stop(self):
        """Stop the remote unlock service"""
        if not self._running:
            return
        
        log.info("Stopping RemoteUnlockService...")
        self._running = False
        
        # Signal shutdown to the async loop
        if self._loop and not self._loop.is_closed() and self._shutdown_event:
            try:
                self._loop.call_soon_threadsafe(self._shutdown_event.set)
            except Exception as e:
                log.error(f"Error signaling shutdown: {e}")
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        log.info("RemoteUnlockService stopped")

    def _run_async_loop(self):
        """Run the async event loop in the thread"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_main())
        except Exception as e:
            log.error(f"Error in RemoteUnlockService async loop: {e}")
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()

    async def _async_main(self):
        """Main async function that handles the Supabase subscription"""
        try:
            # Create shutdown event in the async context
            self._shutdown_event = asyncio.Event()
            
            log.info("Setting up Supabase real-time subscription...")
            
            # Setup real-time subscription
            channel = await self._setup_realtime_subscription()
            if not channel:
                log.error("Failed to setup Supabase subscription")
                return
            
            log.info("Listening for remote lock commands...")
            
            # Keep the subscription alive until shutdown
            try:
                await self._shutdown_event.wait()
            except Exception as e:
                log.error(f"Error waiting for shutdown event: {e}")
            
        except Exception as e:
            log.error(f"Error in RemoteUnlockService main loop: {e}")
        finally:
            log.info("RemoteUnlockService async main loop finished")

    async def _setup_realtime_subscription(self):
        """Setup real-time subscription to lock_commands table"""
        try:
            channel = self.supabase_realtime.channel("remote-lock-commands")

            channel.on_postgres_changes(
                event="INSERT",
                schema="public",
                table="lock_commands",
                filter=f"lock_id=eq.{self.lock_id}",
                callback=self._handle_lock_command_sync,
            )

            await channel.subscribe()
            log.info(f"✅ Subscribed to lock commands for {self.lock_id}")
            return channel
            
        except Exception as e:
            log.error(f"Failed to setup subscription: {e}")
            return None

    def _handle_lock_command_sync(self, payload):
        """Synchronous wrapper for async lock command handler"""
        try:
            # Instead of using asyncio.run_coroutine_threadsafe, 
            # we'll handle this synchronously since we're already in the right thread
            # and use threading to handle the actual unlock
            self._handle_lock_command_threaded(payload)
        except Exception as e:
            log.error(f"Error in lock command sync wrapper: {e}")

    def _handle_lock_command_threaded(self, payload):
        """Handle lock command in a separate thread to avoid blocking"""
        def process_command():
            try:
                # Extract record from payload
                data = payload.get("data", {})
                record = data.get("record", {})
                
                lock_id = record.get("lock_id")
                command = record.get("command")
                created_by = record.get("created_by")
                created_at = record.get("created_at")

                log.info(f"📨 Received remote command: {command} for lock: {lock_id}")
                
                # Validate command
                if lock_id != self.lock_id:
                    log.info(f"⏭️ Ignoring command for different lock: {lock_id}")
                    return
                    
                if command != "unlock":
                    log.info(f"⏭️ Ignoring non-unlock command: {command}")
                    return
                
                if not self.lock_accessory:
                    log.error("❌ No lock accessory available")
                    return

                # Process unlock command
                log.info(f"🔓 Processing remote unlock command from user: {created_by or 'unknown'}")
                
                # Check if already unlocking to prevent race conditions
                if self.is_unlocking:
                    log.info("🔄 Unlock already in progress, ignoring remote command")
                    return
                
                # Trigger remote unlock (synchronously)
                success = self._trigger_remote_unlock_sync()
                
                if success:
                    log.info("✅ Remote unlock completed successfully")
                else:
                    log.error("❌ Remote unlock failed")

            except Exception as e:
                log.error(f"Error handling remote lock command: {e}")
        
        # Run in a separate thread to avoid blocking the realtime subscription
        thread = threading.Thread(target=process_command, daemon=True)
        thread.start()

    def _trigger_remote_unlock_sync(self) -> bool:
        """Trigger remote unlock using the lock accessory (synchronous version)"""
        if self.is_unlocking:
            return False
        
        try:
            self.is_unlocking = True
            
            # Call the lock accessory's remote unlock method
            if hasattr(self.lock_accessory, 'remote_unlock'):
                success = self.lock_accessory.remote_unlock()
                return success
            else:
                log.error("Lock accessory does not support remote unlock")
                return False
                
        except Exception as e:
            log.error(f"Error during remote unlock: {e}")
            return False
        finally:
            self.is_unlocking = False

    def __del__(self):
        """Cleanup when service is destroyed"""
        self.stop()