from ninetyfive.git import parse_numstat, parse_tree


def test_parse_numstat():
    output = "1\t2\ta.py\n-\t-\timage.png\n"
    assert parse_numstat(output) == [
        {"additions": 1, "deletions": 2, "to": "a.py"},
        {"additions": None, "deletions": None, "to": "image.png"},
    ]


def test_parse_tree():
    output = "100644 blob abc123     42\tdir/a file.py\n"
    assert parse_tree(output) == [
        {"mode": "100644", "type": "blob", "object": "abc123", "size": 42, "file": "dir/a file.py"}
    ]
