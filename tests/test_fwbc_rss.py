from fwbc_rss import parse

# mirrors the page's broken markup: stray </tr>, rows without <tr>, an undated row
HTML = """<table><tr><td colspan="10"><h2>October 2026</h2></td></tr></tr>
<td>10/25/26, Sun AM</td><td>Saul's Envy of David</td>
<td><a href="https://www.faithfulwordbaptist.org/102526a.mp3"><img/></a>
<a href="https://rumble.com/x"><img/></a></td><td>Pastor Anderson</td></tr>
</tr><td>10/23/26, Fri PM</td><td>Biblical Manhood</td>
<td><a href="http://www.faithfulwordbaptist.org/102326p.mp3"><img/></a></td><td>Pastor Anderson</td></tr>
</tr><td>06/2013, Series</td><td>Revelation 21</td>
<td><a href="http://www.faithfulwordbaptist.org/revelation_21.mp3"><img/></a></td><td>Pastor Anderson</td></tr></table>"""


def test_parse():
    rows = list(parse(HTML))
    assert [(r[0], r[1], r[2]) for r in rows] == [
        ("https://www.faithfulwordbaptist.org/102526a.mp3", "Saul's Envy of David", "Pastor Anderson"),
        ("https://www.faithfulwordbaptist.org/102326p.mp3", "Biblical Manhood", "Pastor Anderson"),
    ]
    assert rows[0][3].hour == 10 and rows[1][3].hour == 18


if __name__ == "__main__":
    test_parse()
    print("ok")
