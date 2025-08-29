def time_revision(three_times_revision, four_times_revision):
    """
    转换时次订正参数，段、点格式转为单点格式
    Converts time revision parameters into lists '2000-2001,2018,2010-2015'.

    Args:
        four_times_revision (str): 三次订正输入参数，格式：'2000-2001,2018,2010-2015'
        three_times_revision (str): 四次订正输入参数，格式：'2000-2001,2018,2010-2015'

    Returns:
        tuple: A tuple containing the four times revision list and the three times revision list.
    """
    # 时次订正参数转化为列表 '2000-2001,2018,2010-2015'
    all_three = []
    if three_times_revision is not None and three_times_revision != '':
        three_times_revision = three_times_revision.split(',')
        for num, three in enumerate(three_times_revision):
            three = three.split('-')
            if len(three) > 1:
                three = list(range(int(three[0]), int(three[1]) + 1))
            all_three += three
        all_three = [int(x) for x in all_three]
        all_three = list(set(all_three))  # 去除重复

    all_four = []
    if four_times_revision is not None and four_times_revision != '':
        four_times_revision = four_times_revision.split(',')
        for num, four in enumerate(four_times_revision):
            four = four.split('-')
            if len(four) > 1:
                four = list(range(int(four[0]), int(four[1]) + 1))
            all_four += four
        all_four = [int(x) for x in all_four]
        all_four = list(set(all_four))  # 去除重复
    return all_three, all_four


def height_revision(height_revision_year, measure_height, profile_index_main):
    """
    转换高度订正参数格式
    A function that performs height revision parameter conversion.
    时段 -> 时点，三个参数个数对齐

    Parameters:
    - height_revision_year (list): ['1990,2000', '2005,2010', '2015,2018'] 高度订正的时段列表
                                   A list of strings representing height revision years.
    - measure_height (list): [70, 90, 100] 每个时段的高度 A list of height measurements.
    - profile_index_main (list): [1.5, 1.6, 1.7] 每个时段的风廓线指数 A list of profile indexes.

    Returns:
    - new_years (list): A list of new height revision years.
    - new_height (list): A list of new height measurements.
    - new_index (list): A list of new profile indexes.
    """
    # 高度订正参数转换
    if not height_revision_year:
        return None, None, None

    new_years = []
    new_height = []
    new_index = []
    for i in range(len(height_revision_year)):
        h_year = height_revision_year[i].split(',')
        h_years = list(range(int(h_year[0]), int(h_year[1]) + 1))
        num_years = len(h_years)

        height = measure_height[i]
        heights = [height] * num_years

        index = profile_index_main[i]
        indexes = [index] * num_years

        new_years = new_years + h_years
        new_height = new_height + heights
        new_index = new_index + indexes

    return new_years, new_height, new_index


def get_station(main_station, sub_station):
    if not sub_station:
        return main_station
    return main_station + ',' + sub_station


if __name__ == '__main__':
    three_times_revision = '2000-2001,2018,2011,2010-2015'
    three_times_revision = ''
    if three_times_revision:
        print('不空')
    four_times_revision = '2000-2001,2018,2012,2010-2015'
    t, f = time_revision(three_times_revision, four_times_revision)
    if t:
        print("有值")

    print(t, f)

    height_revision_year = ['1990,2000', '2005,2010', '2015,2018']
    measure_height = [70, 90, 100]
    profile_index_main = [1.5, 1.6, 1.7]
    y, h, i = height_revision(height_revision_year, measure_height, profile_index_main)
    print(y, h, i)
