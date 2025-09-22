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
        
        # Connection management
        self._channel = None
        self._reconnect_delay = 5  # seconds
        self._max_reconnect_delay = 60  # seconds
        self._reconnect_attempts = 0
        
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
        """Main async function that handles the Supabase subscription with reconnection"""
        try:
            # Create shutdown event in the async context
            self._shutdown_event = asyncio.Event()
            
            log.info("Starting RemoteUnlockService with auto-reconnection...")
            
            # Keep trying to maintain connection until shutdown
            while self._running:
                try:
                    # Setup real-time subscription
                    await self._setup_realtime_subscription_with_retry()
                    
                    if self._channel:
                        log.info("Listening for remote lock commands...")
                        # Monitor connection and wait for shutdown or connection loss
                        await self._monitor_connection()
                        
                        # If we reach here, either shutdown was requested or connection was lost
                        if not self._running:
                            log.info("Service shutdown requested")
                            break
                        else:
                            # Connection was lost, clean up before retry
                            log.warning("Connection lost, cleaning up before reconnection...")
                            if self._channel:
                                try:
                                    await self._channel.unsubscribe()
                                except:
                                    pass
                                self._channel = None
                    else:
                        log.error("Failed to establish subscription after retries")
                        
                    # If we're still running but lost connection, wait before retry
                    if self._running and not self._shutdown_event.is_set():
                        delay = min(self._reconnect_delay * (2 ** min(self._reconnect_attempts, 4)), self._max_reconnect_delay)
                        log.info(f"Reconnecting in {delay} seconds... (attempt {self._reconnect_attempts + 1})")
                        try:
                            await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                            # Shutdown requested during wait
                            break
                        except asyncio.TimeoutError:
                            # Timeout reached, continue with reconnection
                            self._reconnect_attempts += 1
                        
                except Exception as e:
                    log.error(f"Error in subscription loop: {e}")
                    if self._running:
                        delay = min(self._reconnect_delay * (2 ** min(self._reconnect_attempts, 4)), self._max_reconnect_delay)
                        log.info(f"Reconnecting after error in {delay} seconds...")
                        try:
                            await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                            break
                        except asyncio.TimeoutError:
                            self._reconnect_attempts += 1
            
        except Exception as e:
            log.error(f"Error in RemoteUnlockService main loop: {e}")
        finally:
            # Clean up on exit
            if self._channel:
                try:
                    await self._channel.unsubscribe()
                except:
                    pass
            log.info("RemoteUnlockService async main loop finished")

    async def _setup_realtime_subscription_with_retry(self):
        """Setup real-time subscription with retry logic"""
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                log.info(f"Setting up Supabase real-time subscription (attempt {attempt + 1}/{max_retries})...")
                
                # Clean up any existing channel first
                if self._channel:
                    try:
                        await self._channel.unsubscribe()
                    except:
                        pass
                    self._channel = None
                
                # Create new client instance for fresh connection
                self.supabase_realtime = AsyncClient(self.supabase_url, self.supabase_anon_key)
                
                # Use a unique channel name to avoid conflicts
                channel_name = f"remote-lock-commands-{attempt}-{int(asyncio.get_event_loop().time())}"
                channel = self.supabase_realtime.channel(channel_name)

                # Add error handler for the channel
                def on_error(error, *args):
                    log.error(f"Channel error: {error}")
                    # Mark channel as None to trigger reconnection
                    self._channel = None

                def on_close(*args):
                    log.warning("Channel closed, will attempt reconnection")
                    self._channel = None

                # Set up event handlers if available
                if hasattr(channel, 'on_error'):
                    channel.on_error(on_error)
                if hasattr(channel, 'on_close'):
                    channel.on_close(on_close)

                channel.on_postgres_changes(
                    event="INSERT",
                    schema="public",
                    table="lock_commands",
                    filter=f"lock_id=eq.{self.lock_id}",
                    callback=self._handle_lock_command_sync,
                )

                # Subscribe with timeout to detect stuck connections
                try:
                    await asyncio.wait_for(channel.subscribe(), timeout=30.0)
                except asyncio.TimeoutError:
                    log.error("Subscription timeout - connection may be stuck")
                    raise ConnectionError("Subscription timeout")
                
                self._channel = channel
                self._reconnect_attempts = 0  # Reset on successful connection
                log.info(f"✅ Successfully subscribed to lock commands for {self.lock_id} (channel: {channel_name})")
                return
                
            except Exception as e:
                log.error(f"Subscription attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 16)  # Cap at 16 seconds
                    log.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    log.error("All subscription attempts failed")
                    self._channel = None

    async def _monitor_connection(self):
        """Monitor connection and handle disconnections"""
        try:
            # Wait for either shutdown or connection issues
            while self._running and self._channel:
                try:
                    # Check if we should shutdown with shorter timeout for better responsiveness
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=10.0)
                    # Shutdown requested
                    log.info("Shutdown requested, stopping connection monitoring")
                    break
                except asyncio.TimeoutError:
                    # Timeout reached, check connection health
                    if not self._running:
                        break
                    
                    # Check if channel is still alive by examining connection state
                    try:
                        # Try to access channel state - this may raise if disconnected
                        if hasattr(self._channel, '_socket') and self._channel._socket:
                            if self._channel._socket.closed:
                                log.warning("WebSocket connection detected as closed")
                                raise ConnectionError("WebSocket connection closed")
                    except Exception as e:
                        log.warning(f"Connection health check failed: {e}")
                        raise ConnectionError(f"Connection unhealthy: {e}")
                    
                    continue
                    
        except (ConnectionError, Exception) as e:
            log.error(f"Connection lost or monitoring error: {e}")
            # Mark channel as None to trigger reconnection
            self._channel = None
            # Don't raise - let the main loop handle reconnection

    async def _setup_realtime_subscription(self):
        """Legacy method - now handled by _setup_realtime_subscription_with_retry"""
        # Keep this for compatibility but redirect to new method
        await self._setup_realtime_subscription_with_retry()
        return self._channel

    def _handle_lock_command_sync(self, payload):
        """Synchronous wrapper for async lock command handler"""
        try:
            # Check if we're still running and have a valid connection
            if not self._running or not self._channel:
                log.warning("Received command but service is not active")
                return
                
            # Handle the command in a separate thread to avoid blocking
            self._handle_lock_command_threaded(payload)
        except Exception as e:
            log.error(f"Error in lock command sync wrapper: {e}")
            # Don't crash on individual command errors

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