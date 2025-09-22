#!/usr/bin/env python3
"""
Remote Unlock Service
Simple Supabase real-time subscription for remote lock commands.
"""

import asyncio
import threading
import logging
from typing import Optional
from supabase import create_client, Client

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
        
        # Create synchronous Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_anon_key)
        
        # Simple state management
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._channel = None
        
        log.info(f"RemoteUnlockService initialized for lock_id: {lock_id}")

    def start(self):
        """Start the remote unlock service"""
        if self._running:
            log.warning("RemoteUnlockService is already running")
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
        
        # Unsubscribe from channel
        if self._channel:
            try:
                self._channel.unsubscribe()
            except Exception as e:
                log.error(f"Error unsubscribing: {e}")
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        log.info("RemoteUnlockService stopped")

    def _run(self):
        """Main run loop - sets up subscription and waits"""
        try:
            # Create channel for lock commands
            self._channel = self.supabase.channel(f"lock-commands-{self.lock_id}")
            
            # Subscribe to INSERT events on lock_commands table
            self._channel.on_postgres_changes(
                event="INSERT",
                schema="public", 
                table="lock_commands",
                filter=f"lock_id=eq.{self.lock_id}",
                callback=self._handle_lock_command
            )
            
            # Subscribe to the channel
            self._channel.subscribe()
            log.info(f"✅ Subscribed to lock commands for {self.lock_id}")
            
            # Keep the thread alive while running
            while self._running:
                threading.Event().wait(1)  # Sleep for 1 second
            
        except Exception as e:
            log.error(f"Error in RemoteUnlockService: {e}")
        finally:
            if self._channel:
                try:
                    self._channel.unsubscribe()
                except:
                    pass

    def _handle_lock_command(self, payload: dict):
        """Handle incoming lock command from Supabase"""
        try:
            # Extract record data
            data = payload.get("data", {})
            record = data.get("record", {})
            
            lock_id = record.get("lock_id")
            command = record.get("command")
            created_by = record.get("created_by")

            log.info(f"📨 Received command: {command} for lock: {lock_id}")
            
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
            log.info(f"🔓 Processing unlock command from: {created_by or 'unknown'}")
            
            # Trigger unlock in separate thread to avoid blocking
            threading.Thread(
                target=self._execute_unlock,
                args=(created_by,),
                daemon=True
            ).start()

        except Exception as e:
            log.error(f"Error handling lock command: {e}")

    def _execute_unlock(self, created_by):
        """Execute the unlock operation"""
        try:
            if hasattr(self.lock_accessory, 'remote_unlock'):
                success = self.lock_accessory.remote_unlock()
                if success:
                    log.info(f"✅ Remote unlock successful for user: {created_by}")
                else:
                    log.error("❌ Remote unlock failed")
            else:
                log.error("Lock accessory does not support remote unlock")
                
        except Exception as e:
            log.error(f"Error executing unlock: {e}")

    def __del__(self):
        """Cleanup when service is destroyed"""
        self.stop()