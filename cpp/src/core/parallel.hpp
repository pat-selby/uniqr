// Split a loop over rows across the processor's cores.
//
// Image work on a whole screen is the slow part of a scan, and rows are
// independent, so each thread takes a band of them. Small images stay on one
// thread: starting threads costs more than it saves below a few dozen rows each.

#pragma once

#include <algorithm>
#include <thread>
#include <vector>

namespace uniqr {

template <class Fn>
void parallel_rows(int rows, Fn&& fn, int min_rows_per_thread = 64) {
    if (rows <= 0) return;
    const int cores = static_cast<int>(std::max(1u, std::thread::hardware_concurrency()));
    const int bands = std::min(cores, std::max(1, rows / min_rows_per_thread));
    if (bands <= 1) {
        fn(0, rows);
        return;
    }
    const int step = (rows + bands - 1) / bands;
    std::vector<std::thread> threads;
    threads.reserve(bands);
    for (int begin = 0; begin < rows; begin += step) {
        const int end = std::min(rows, begin + step);
        threads.emplace_back([&fn, begin, end] { fn(begin, end); });
    }
    for (auto& t : threads) t.join();
}

}  // namespace uniqr
