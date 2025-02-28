# grpc_pool_manager.py
import asyncio
import grpc
from grpc.aio import insecure_channel
from contextlib import asynccontextmanager
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class GlobalGrpcPool:
    def __init__(self, max_channels=50, buffer_size=5, channel_options=None):
        self._initialized = False
        self.max_channels = max_channels
        self.buffer_size = buffer_size
        # Use separate queue per target
        self.available_queues = defaultdict(lambda: asyncio.Queue(maxsize=self.buffer_size))
        self.semaphore = asyncio.Semaphore(self.max_channels - self.buffer_size)
        self.channel_options = channel_options or [
            ("grpc.max_send_message_length", 100 * 1024 * 1024),  # 100 MB
            ("grpc.max_receive_message_length", 100 * 1024 * 1024),  # 100 MB
            ("grpc.keepalive_timeout_ms", 3600000),  # 1 hour
            ("grpc.keepalive_timeout_ms", 50 * 1000),  # 50 seconds
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_time_between_pings_ms", 10 * 1000),  # 10 seconds
            ("grpc.max_connection_idle_ms", 60 * 60 * 1000),  # 1 hour
            ("grpc.max_connection_age_ms", 2 * 60 * 60 * 1000),  # 2 hours
        ]
        self.channel_stats = defaultdict(lambda: {"acquired": 0, "released": 0, "total_channels": 0})
        self._initialized = True
        logger.info(
            f"GlobalGrpcPool initialized with max_channels={self.max_channels} and buffer_size={self.buffer_size}"
        )

    async def get_channel(self, target: str):
        await self.semaphore.acquire()
        try:
            # Get queue specific to this target
            target_queue = self.available_queues[target]
            
            if not target_queue.empty():
                channel = await target_queue.get()
                logger.info(f"Reusing channel from buffer for {target}")
            else:
                channel = insecure_channel(target, options=self.channel_options)
                self.channel_stats[target]["total_channels"] += 1
                logger.info(f"New channel created for {target}")
            
            self.channel_stats[target]["acquired"] += 1
            return channel
        except Exception as e:
            logger.error(f"Error acquiring channel for {target}: {e}")
            self.semaphore.release()
            raise

    async def release_channel(self, target: str, channel):
        if channel is None:
            self.semaphore.release()
            return

        try:
            connectivity = channel.get_state(True)
            if connectivity == grpc.ChannelConnectivity.SHUTDOWN:
                logger.warning(f"Channel for {target} is shutdown")
                self.channel_stats[target]["total_channels"] -= 1
                self.channel_stats[target]["released"] += 1
                self.semaphore.release()
                return

            target_queue = self.available_queues[target]
            try:
                target_queue.put_nowait(channel)
                self.channel_stats[target]["released"] += 1
                logger.info(f"Channel released back to buffer for {target}")
            except asyncio.QueueFull:
                await channel.close()
                self.channel_stats[target]["total_channels"] -= 1
                self.channel_stats[target]["released"] += 1
        finally:
            self.semaphore.release()

    async def close_all(self):
        """Safely close all gRPC channels in the pool."""
        logger.info("Closing all channels in the pool.")
        try:
            # Create list of cleanup tasks
            cleanup_tasks = []
            
            # Iterate through all queues in the defaultdict
            for target, queue in self.available_queues.items():
                while not queue.empty():
                    try:
                        channel = await asyncio.wait_for(queue.get(), timeout=5.0)
                        if channel:
                            # Create task for closing channel
                            cleanup_tasks.append(
                                asyncio.create_task(self._close_channel(target, channel))
                            )
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout while getting channel from queue for {target}")
                    except Exception as e:
                        logger.error(f"Error getting channel from queue for {target}: {e}")

            # Wait for all cleanup tasks to complete
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
            # Clear the queues
            self.available_queues.clear()
            
            logger.info("All buffered channels have been closed.")
        except Exception as e:
            logger.error(f"Error during pool cleanup: {e}")
            raise

    async def _close_channel(self, target: str, channel):
        """Helper method to safely close a single channel."""
        try:
            await channel.close()
            self.channel_stats[target]["total_channels"] -= 1
            self.channel_stats[target]["released"] += 1
            logger.debug(f"Successfully closed channel for {target}")
        except Exception as e:
            logger.error(f"Error closing channel for {target}: {e}")

    def print_stats(self):
        for target, stats in self.channel_stats.items():
            logger.info(
                f"Stats for {target}: Acquired={stats['acquired']}, Released={stats['released']}, Total Channels={stats['total_channels']}"
            )

    @asynccontextmanager
    async def channel_context(self, target: str):
        channel = await self.get_channel(target)
        try:
            yield channel
        finally:
            await self.release_channel(target, channel)

    async def monitor_pool(self, interval: int = 60):
        """
        Periodically logs the pool statistics.
        """
        while True:
            await asyncio.sleep(interval)
            self.print_stats()


# Singleton accessor functions
_pool_instance = None


def get_grpc_pool_instance(
    max_channels=50, buffer_size=5, channel_options=None
) -> GlobalGrpcPool:
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = GlobalGrpcPool(
            max_channels=max_channels,
            buffer_size=buffer_size,
            channel_options=channel_options,
        )
        logger.info("GlobalGrpcPool instance created.")
    return _pool_instance


async def close_grpc_pool():
    global _pool_instance
    if _pool_instance:
        await _pool_instance.close_all()
        _pool_instance = None
        logger.info("GlobalGrpcPool instance closed and cleared.")
