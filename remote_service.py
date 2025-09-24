#!/usr/bin/env python3
"""
Remote Unlock Service
Simple and reliable Supabase real-time subscription for remote lock commands.
"""

import asyncio
import threading
import logging
from typing import Optional
from supabase import AsyncClient, AsyncClientOptions
from supabase.types import RealtimeClientOptions, RealtimeSubscribeStates

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
        self._loop = None
        self._subscribe_task = None
        
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
        
        # Cancel the subscribe task if it exists
        if self._subscribe_task and not self._subscribe_task.done():
            self._subscribe_task.cancel()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        log.info("RemoteUnlockService stopped")

    def _run(self):
        """Main service loop - uses built-in Supabase reconnection"""
        try:
            # Create a single event loop for the entire service
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Run the subscription
            self._loop.run_until_complete(self._subscribe_and_listen())
            
        except Exception as e:
            log.error(f"Service error: {e}")
        finally:
            # Cleanup
            if self._channel:
                try:
                    self._loop.run_until_complete(self._cleanup())
                except Exception as cleanup_error:
                    log.debug(f"Cleanup error: {cleanup_error}")
            
            if self._loop:
                try:
                    self._loop.close()
                except:
                    pass

    async def _cleanup(self):
        """Properly cleanup resources"""
        try:
            if self._channel:
                # Only unsubscribe if we're actually stopping the service
                if not self._running:
                    await self._channel.unsubscribe()
                    log.info("Channel unsubscribed")
            
            if self._client:
                # Close the client connection
                await self._client.realtime.close()
                log.info("Client connection closed")
                
        except Exception as e:
            log.debug(f"Cleanup exception: {e}")
        finally:
            self._client = None
            self._channel = None

    async def _subscribe_and_listen(self):
        """Subscribe to Supabase and listen for commands with built-in reconnection"""
        # Create client with automatic reconnection enabled
        self._client = AsyncClient(
            self.supabase_url, 
            self.supabase_anon_key, 
            AsyncClientOptions(
                realtime=RealtimeClientOptions(
                    auto_reconnect=True,  # Let Supabase handle reconnection
                    max_retries=10,       # More retries for better reliability
                    hb_interval=30,       # Heartbeat interval
                ),
                persist_session=False
            ),
        )
        
        # Create channel - use a simple, consistent name
        channel_name = f"lock-{self.lock_id}"
        self._channel = self._client.channel(channel_name)
        
        # Set up postgres changes listener
        self._channel.on_postgres_changes(
            event="INSERT",
            schema="public", 
            table="lock_commands",
            filter=f"lock_id=eq.{self.lock_id}",
            callback=self._handle_lock_command
        )
        
        # Subscribe with callback to monitor connection state
        await self._channel.subscribe(callback=self._on_subscribe_callback)
        
        log.info(f"✅ Subscribed to lock commands for {self.lock_id} on channel {channel_name}")
        
        # Keep the service alive - the client will handle reconnections automatically
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            log.info("Subscription cancelled")
        except Exception as e:
            log.error(f"Unexpected error in subscription: {e}")
            raise

    def _on_subscribe_callback(self, status: RealtimeSubscribeStates, err: Optional[Exception]):
        """Handle subscription status changes"""
        if status == RealtimeSubscribeStates.SUBSCRIBED:
            log.info("🟢 Successfully subscribed to realtime channel")
        elif status == RealtimeSubscribeStates.CHANNEL_ERROR:
            log.error(f"🔴 Channel error: {err}")
        elif status == RealtimeSubscribeStates.TIMED_OUT:
            log.warning("🟡 Subscription timed out")
        elif status == RealtimeSubscribeStates.CLOSED:
            log.info("🔵 Channel closed")

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