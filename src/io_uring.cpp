#include <liburing.h>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>

int main() {
    // Initialize io_uring
    struct io_uring ring;
    io_uring_queue_init(8, &ring, 0);

    // Open the file
    int fd = open("/media/xiaochen/large/cs_data/io_uring_test/test_file", O_RDONLY);
    if (fd < 0) {
        std::cerr << "Failed to open file" << std::endl;
        return 1;
    }

    // Set up the buffer and submission queue entry
    char buffer[1024];
    struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
    io_uring_prep_read(sqe, fd, buffer, sizeof(buffer), 0);

    // Submit the request
    io_uring_submit(&ring);

    // Wait for completion
    struct io_uring_cqe *cqe;
    io_uring_wait_cqe(&ring, &cqe);

    // Check result and print
    if (cqe->res >= 0) {
        std::cout.write(buffer, cqe->res);
    } else {
        std::cerr << "Read failed" << std::endl;
    }

    // Cleanup
    io_uring_cqe_seen(&ring, cqe);
    io_uring_queue_exit(&ring);
    close(fd);
    return 0;
}