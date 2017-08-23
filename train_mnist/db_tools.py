import sqlite3
from collections import Counter


def init(db_file):
    conn = sqlite3.connect(db_file)
    sql = '''CREATE TABLE  IF NOT EXISTS  projectfilelist(
                             file_name TEXT,
                             file_list_idx INTEGER,
                             spos_wordset INTEGER,
                             epos_wordset INTEGER,
                             project_name TEXT,
                             file_category INTEGER
                             );'''
    conn.execute(sql)
    conn.execute(u"DELETE FROM projectfilelist")
    return conn


def open_db(db_file):
    conn = sqlite3.connect(db_file)
    return conn


def get_rows(conn):
    cur = conn.cursor()
    cur.execute("SELECT spos_wordset, epos_wordset, file_name FROM projectfilelist")
    rows = cur.fetchall()
    return rows


def close(conn):
    conn.close()


def update_word_index(conn, file_idx, word_cursor, num_word):
    sPos = word_cursor
    ePos = sPos
    
    if num_word > 0:
        ePos = sPos + num_word - 1

    conn.execute(u"""UPDATE projectfilelist
                SET spos_wordset = ?,
                    epos_wordset = ?
                WHERE file_list_idx = ?""", (sPos, ePos, file_idx))
    conn.commit()

    ret = sPos
    if num_word > 0:
        ret = ePos + 1
    
    return ret


def update_project_name(conn, file_names, project_names):
    cur = conn.cursor()
    cur.executemany('UPDATE projectfilelist SET project_name=? WHERE file_name=?', zip(project_names, file_names))
    conn.commit()


def update_file_type(conn, words_type):
    rows = get_rows(conn)
    fileNames = ["" for x in range(len(rows))]
    fileTypes = range(len(rows))
    
    i = 0
    for row in rows:
        sPos = row[0]
        ePos = row[1]
        file_name = row[2]
        fileNames[i] = file_name
        fileTypes[i] = -1
        if sPos is not None:
            print 'idx: (' + str(sPos) + ', ' + str(ePos) + ')'
            count = Counter(words_type[sPos:ePos])
            freq = count.most_common()
            if len(freq) > 0:
                max_freq = freq[0]
                fileTypes[i] = max_freq[0]
                print file_name.decode('utf-8') + ' type: ' + str(max_freq)
        i += 1

    cur = conn.cursor()
    cur.executemany('UPDATE projectfilelist SET file_category=? WHERE file_name=?', zip(fileTypes, fileNames))
    conn.commit()




