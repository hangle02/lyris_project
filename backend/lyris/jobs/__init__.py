"""Việc nền của Phase 3 (docs/phase3.md §4): hàng đợi trong bảng `jobs` và worker chạy trong tiến trình.

- `queue.JobQueue`: xếp job, báo worker khi lượt chat bắt đầu/kết thúc, `pending(story_id)`.
- `worker.Worker`: chạy lần lượt từng job (FIFO), nhường model cho lượt chat.
"""
from lyris.jobs.queue import JobQueue
from lyris.jobs.worker import Worker

__all__ = ["JobQueue", "Worker"]
