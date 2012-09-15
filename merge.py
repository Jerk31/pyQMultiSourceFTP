def merge_files(input_files, out_filename):

    out_file = open(out_filename, 'wb')
    
    for part_file in input_files:
        f = open(part_file, 'r')
    
        chunk = f.read(8192)
        while chunk:
            out_file.write(chunk)
            chunk = f.read(8192)
    
        f.close()
    
    out_file.close()
