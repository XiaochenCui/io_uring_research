#include <liburing.h>
#include <fcntl.h>
#include <unistd.h>
#include <iostream> // for std::cout
#include <iomanip>  // for std::hex, std::setw, and std::setfill
#include <cstring>  // for memset

// The default and easiest way to initialize io_uring. Return 0 for success.
int io_uring_init_1(struct io_uring &ring)
{
    io_uring_queue_init(8, &ring, 0);
    return 0;
}

// Initialize io_uring with parameters. Return 0 for success.
int io_uring_init_2(struct io_uring &ring)
{
    struct io_uring_params params;
    memset(&params, 0, sizeof(params));

    params.flags |= IORING_SETUP_SQPOLL;

    int result = io_uring_queue_init_params(2048, &ring, &params);
    if (result != 0)
    {
        perror("io_uring_init_failed...\n");
        return result;
    }

    // check if IORING_FEAT_FAST_POLL is supported
    if (!(params.features & IORING_FEAT_FAST_POLL))
    {
        printf("IORING_FEAT_FAST_POLL not available in the kernel, quiting...\n");
        return -1;
    }

    return 0;
}

int main()
{
    struct io_uring ring;

    // int init_result = io_uring_init_1(ring);
    int init_result = io_uring_init_2(ring);
    if (init_result != 0)
    {
        return init_result;
    }

    // Open the file
    int fd = open("/media/xiaochen/large/cs_data/io_uring_test/test_file", O_RDONLY);
    if (fd < 0)
    {
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
    if (cqe->res >= 0)
    {
        // std::cout.write(buffer, cqe->res);
        for (int i = 0; i < cqe->res && i <= 10; ++i)
        {
            std::cout << std::hex << std::setw(2) << std::setfill('0')
                      << (static_cast<unsigned int>(buffer[i]) & 0xFF) << " ";
        }
        std::cout << std::dec << std::endl; // Reset to decimal for other output
    }
    else
    {
        std::cerr << "Read failed" << std::endl;
    }

    // Cleanup
    io_uring_cqe_seen(&ring, cqe);
    io_uring_queue_exit(&ring);
    close(fd);
    return 0;
}
