"""冒泡排序示例：按升序排序，并保留原始输入。"""


def bubble_sort(values):
    """返回排序后的新列表，元素需要支持大小比较。

    相邻元素顺序错误时交换，每轮将当前最大值移到末尾。
    如果一轮没有交换，说明已经有序，可以提前结束。
    时间复杂度：最好 O(n)，平均和最坏 O(n²)；额外空间 O(n)。
    """
    result = list(values)

    for end in range(len(result) - 1, 0, -1):
        swapped = False
        for index in range(end):
            if result[index] > result[index + 1]:
                result[index], result[index + 1] = (
                    result[index + 1],
                    result[index],
                )
                swapped = True
        if not swapped:
            break

    return result


if __name__ == "__main__":
    numbers = [64, 34, 25, 12, 22, 11, 90]
    print("排序前：", numbers)
    print("排序后：", bubble_sort(numbers))
