import os, time, tempfile

def cleanup_temp_files(age_seconds=3600):
    now = time.time()
    tmp_dir = tempfile.gettempdir()
    for f in os.listdir(tmp_dir):
        fpath = os.path.join(tmp_dir, f)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < now - age_seconds:
            try:
                os.remove(fpath)
            except:
                pass
