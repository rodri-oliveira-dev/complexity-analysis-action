int Sum(int[] values)
{
    var total = 0;
    foreach (var value in values)
    {
        total += value;
    }

    return total;
}

Console.WriteLine(Sum([1, 2, 3]));
