"""Video decoding: frames come out in order, and bad files fail with a plain message."""

import pytest

from backend.samples import SAMPLES
from backend.video import VideoError, open_video
from scripts.make_sample_video import FRAMES, HEIGHT, WIDTH, write_synthetic_video

SAMPLE_PATH = SAMPLES["synthetic-traffic"].path


def test_the_bundled_sample_decodes_to_every_frame():
    with open_video(SAMPLE_PATH) as video:
        frames = list(video.frames())

    assert video.frame_count == FRAMES
    assert len(frames) == FRAMES
    assert frames[0].shape == (HEIGHT, WIDTH, 3)


def test_the_generator_writes_the_requested_number_of_frames(tmp_path):
    path = tmp_path / "short.mp4"
    write_synthetic_video(path, frames=5)

    with open_video(path) as video:
        assert len(list(video.frames())) == 5


def test_a_missing_file_fails_with_a_plain_message(tmp_path):
    with pytest.raises(VideoError, match="could not be opened"):
        open_video(tmp_path / "missing.mp4")


def test_a_file_that_is_not_a_video_fails_with_a_plain_message(tmp_path):
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"this is not a video")

    with pytest.raises(VideoError, match="could not be opened"):
        open_video(path)
