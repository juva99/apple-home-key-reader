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
        self._shutdown_event = asyncio.Event()
        
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
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        
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
            log.info("Setting up Supabase real-time subscription...")
            
            # Setup real-time subscription
            channel = await self._setup_realtime_subscription()
            if not channel:
                log.error("Failed to setup Supabase subscription")
                return
            
            log.info("Listening for remote lock commands...")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            log.error(f"Error in RemoteUnlockService main loop: {e}")

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
            # Schedule the async handler in the current loop
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self._handle_lock_command_async(payload), 
                    self._loop
                )
        except Exception as e:
            log.error(f"Error in lock command sync wrapper: {e}")

    async def _handle_lock_command_async(self, payload):
        """Handle incoming lock command from Supabase"""
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
            
            # Trigger remote unlock
            success = await self._trigger_remote_unlock()
            
            if success:
                log.info("✅ Remote unlock completed successfully")
            else:
                log.error("❌ Remote unlock failed")

        except Exception as e:
            log.error(f"Error handling remote lock command: {e}")

    async def _trigger_remote_unlock(self) -> bool:
        """Trigger remote unlock using the lock accessory"""
        if self.is_unlocking:
            return False
        
        try:
            self.is_unlocking = True
            
            # Call the lock accessory's remote unlock method
            # This will be implemented in the next step
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