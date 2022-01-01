from pathlib import Path

from loguru import logger

from skylark.gateway.chunk_store import Chunk, ChunkRequest, ChunkRequestHop, ChunkState
from skylark.gateway.gateway_daemon import GatewayDaemon
from skylark.replicate.obj_store import S3Interface

if __name__ == "__main__":
    daemon = GatewayDaemon("/dev/shm/skylark/chunks", debug=True)

    # make obj store interfaces
    src_obj_interface = S3Interface("us-east-1", "skylark-us-east-1")
    dst_obj_interface = S3Interface("us-west-1", "skylark-us-west-1")
    obj = "/test.txt"

    # make random test.txt file and upload it if it doesn't exist
    if not src_obj_interface.exists(obj):
        logger.info(f"Uploading {obj} to {src_obj_interface.bucket_name}")
        test_file = Path("/tmp/test.txt")
        test_file.write_text("test")
        src_obj_interface.upload_object(test_file, obj).result()

    # make chunk request
    file_size_bytes = src_obj_interface.get_obj_size(obj)
    chunk = Chunk(
        key=obj,
        chunk_id=0,
        file_offset_bytes=0,
        chunk_length_bytes=file_size_bytes,
        chunk_hash_sha256=None,
    )
    src_path = ChunkRequestHop(
        hop_cloud_region="aws:us-east-1",
        hop_ip_address="localhost",
        chunk_location_type="relay",
        src_object_store_region="us-east-1",
        src_object_store_bucket="skylark-us-east-1",
    )
    req = ChunkRequest(chunk=chunk, path=[src_path])
    logger.debug(f"Chunk request: {req}")

    # send chunk request to gateway
    daemon.chunk_store.add_chunk_request(req, ChunkState.ready_to_upload)
    assert daemon.chunk_store.get_chunk_request(req.chunk.chunk_id) == req

    # run gateway daemon
    daemon.run()