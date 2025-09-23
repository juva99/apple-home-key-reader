#!/usr/bin/env python3
"""
Remote Unlock Service
Simple and reliable Supabase real-time subscription for remote lock commands.
"""

import asyncio
import threading
import logging
import time
from typing import Optional
from supabase import AsyncClient, AsyncClientOptions
from supabase.types import RealtimeClientOptions

# Suppress verbose logging from Supabase client libraries
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("supabase").setLevel(logging.WARNING)
logging.getLogger("postgrest").setLevel(logging.WARNING)
logging.getLogger("realtime").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


class RemoteUnlockService:
    """Simple service that subscribes to Supabase for remote lock commands"""
    
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
        
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._client = None
        self._channel = None
        self._channel_name = f"lock-commands-{self.lock_id}"  # Remove timestamp
        
        log.info(f"RemoteUnlockService initialized for lock_id: {lock_id}")

    def start(self):
        """Start the remote unlock service"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("RemoteUnlockService started")

    def stop(self):
        """Stop the remote unlock service"""
        if not self._running:
            return
        
        log.info("Stopping RemoteUnlockService...")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        
        log.info("RemoteUnlockService stopped")

    def _run(self):
        """Main service loop - handles reconnection automatically"""
        while self._running:
            try:
                # Run async subscription
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._subscribe_and_listen())
            except Exception as e:
                log.error(f"Service error: {e}")
            finally:
                # Cleanup
                if self._channel:
                    try:
                        loop.run_until_complete(self._cleanup_channel())
                    except Exception as cleanup_error:
                        log.debug(f"Cleanup error (expected): {cleanup_error}")
                
                if self._client:
                    try:
                        # Don't close the client, let it handle reconnection
                        pass
                    except:
                        pass
                
                if loop:
                    try:
                        loop.close()
                    except:
                        pass
                # Reset state
                self._client = None
                self._channel = None
                
                # Wait before reconnecting
                if self._running:
                    log.info("Reconnecting in 5 seconds...")
                    time.sleep(5)

    async def _cleanup_channel(self):
        """Properly cleanup the channel"""
        if self._channel:
            try:
                await self._channel.unsubscribe()
            except:
                pass

    async def _subscribe_and_listen(self):
        """Subscribe to Supabase and listen for commands"""
        # Create client with better reconnection settings
        self._client = AsyncClient(
            self.supabase_url, 
            self.supabase_anon_key, 
            AsyncClientOptions(
                realtime=RealtimeClientOptions(
                    auto_reconnect=False,  # Handle reconnection ourselves
                    max_retries=3,
                    hb_interval=30,
                ),
                persist_session=False  # Don't persist session to avoid conflicts
            ),
        )
        
        # Create channel with consistent name
        self._channel = self._client.channel(self._channel_name)
        
        # Subscribe to postgres changes
        self._channel.on_postgres_changes(
            event="INSERT",
            schema="public", 
            table="lock_commands",
            filter=f"lock_id=eq.{self.lock_id}",
            callback=self._handle_lock_command
        )
        
        # Subscribe and wait
        await self._channel.subscribe()
        log.info(f"✅ Subscribed to lock commands for {self.lock_id} on channel {self._channel_name}")
        
        # Keep alive - this will throw exception when connection fails
        while self._running:
            await asyncio.sleep(1)
            
            # Check if channel is still subscribed
            if hasattr(self._channel, '_state') and self._channel._state == 'closed':
                log.warning("Channel closed, triggering reconnection...")
                raise ConnectionError("Channel was closed")

    def _handle_lock_command(self, payload: dict):
        """Handle incoming lock command"""
        try:
            # Extract data
            data = payload.get("data", {})
            record = data.get("record", {})
            
            lock_id = record.get("lock_id")
            command = record.get("command")
            created_by = record.get("created_by", "unknown")

            # Validate
            if lock_id != self.lock_id or command != "unlock":
                return
            
            if not self.lock_accessory:
                log.error("❌ No lock accessory available")
                return

            log.info(f"🔓 Processing unlock command from: {created_by}")
            
            # Execute unlock (sync operation)
            if hasattr(self.lock_accessory, 'remote_unlock'):
                success = self.lock_accessory.remote_unlock()
                if success:
                    log.info(f"✅ Remote unlock successful")
                else:
                    log.error("❌ Remote unlock failed")
            else:
                log.error("❌ Lock accessory does not support remote unlock")
                
        except Exception as e:
            log.error(f"Error handling command: {e}")

    def __del__(self):
        self.stop()