import re
import logging

logger = logging.getLogger(__name__)

path = 'var/log/uwsgi/req-log/req.log'
path_out = 'var/log/uwsgi/log-analys-results/out.txt'
pattern = r"(GET|POST|PUT|DELETE)\s+(/[^\s?]+)"
patter2 = r"/([^/]+)"
pattern3 = r"\[\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}\]"

timestamp_first_line = " "
timestamp_last_line = " "

count_get_products = { 'products': [] }


# Extract first and last line of file
try:
    req_log_file = open(path, 'r')

    # Read first line of file 
    first_line = req_log_file.readline()
    # Extract timestamp of line ( http request )
    match_timestamp_first = re.search(pattern3, str(first_line))
    timestamp_first_line = match_timestamp_first.group()
    
    # Read last line of file 
    last_line = req_log_file.readlines()[-1:]
    # Extract timestamp of line ( http request )
    match_timestamp_last = re.search(pattern3, str(last_line))
    timestamp_last_line = match_timestamp_last.group()

    req_log_file.close()
except Exception as e:
    logger.exception("Error extracting first and last timestamp from request log")


# Collect all GET requests for '/products'
try:
    req_log_file = open(path, 'r')

    for line in req_log_file:

        # Extracts the pattern from the line
        match = re.search(pattern, line)

        if match:
            # Extracts only the route - after GET
            route = match.group(2)

            # Extracts every field of the route
            match2 = re.findall(patter2, route)

            # If the first field of the route equals 'products'
            if match2[0] == 'products' :

                # I add the route to the dict
                count_get_products['products'].append(route)

    req_log_file.close()

except Exception as e:
    logger.exception("Error reading request log")

# Creating out structure for counting and sorting 
out = []

# For all 'products' routes aggregated in step 1
# Basic idea: if there is one, the count field is incremented, if not, it is inserted.
for route in count_get_products['products']:
    if len(out) == 0:
        out.append( [route, 0] )
    else:
        flag = False
        for elem in out:
            if elem[0] == route:
                elem[1] += 1
                flag = True
        if flag is False:
            out.append( [route, 0])

# Sort out in descending order
out_sorted = sorted(out, key=lambda x: x[1], reverse=True)

# Writing result to file
try: 
    file_out = open(path_out, 'w')
    file_out.write("\n\n Start analysis from " + timestamp_first_line + " to " + timestamp_last_line + '\n\n\n')
    for elem in out_sorted:
        file_out.write("route : " + elem[0] + " - count : " + str(elem[1]) + '\n') 
    file_out.close() 
except Exception as e:
    logger.exception("Error writing log analysis output")





