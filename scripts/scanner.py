import functools
import http.server
import json
import os
import pathlib
import requests
import socketserver
import tkinter as tk
from tkinter import filedialog, Text, Entry
import webbrowser

scripts_path = pathlib.Path().absolute()

def startGui():

    root = tk.Tk()

    def openDashboard():

        if check_db_info(api_key_input.get(), db_url_input.get()):

            activities_path = filedialog.askdirectory(title="Select activities folder")

            activities = find_activities(activities_path)

            connections = find_connections(activities, activities_path)
            links_amount = get_links_amount(api_key_input.get(), db_url_input.get())
            converted_connections = convert_connections(connections, activities_path, links_amount)
            store_connections(converted_connections)
            run_server()
        
    def convertApp():

        if check_db_info(api_key_input.get(), db_url_input.get()):
            activities_path = filedialog.askdirectory(title="Select activities folder")

            activities = find_activities(activities_path)
            enable_internet_access(activities_path)
            add_oncreate_trackers(activities, activities_path, api_key_input.get(), db_url_input.get())

    # check if restdb info is correct
    def check_db_info(api_key, db_url):

        headers = {
        'content-type': "application/json",
        'x-apikey': "%s" % api_key,
        'cache-control': "no-cache"
        }

        try:
            response = requests.request("GET", db_url, headers=headers)
            if response.status_code ==  200:
                return True

            else:
                print("Incorrect RestDB info entered, please try again")
                return False

        except (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema):
            print("Incorrect RestDB info entered, please try again")

    canvas = tk.Canvas(root, height=300, width=700, bg="#c4c4c4")
    canvas.pack()

    frame = tk.Frame(root, bg="white")
    frame.place(relwidth=0.9, relheight=0.8, relx=0.05, rely=0.05)

    db_url_input = Entry(frame)
    db_url_input.pack()
    db_url_input.insert(0, "DB URL")

    api_key_input = Entry(frame)
    api_key_input.pack()
    api_key_input.insert(0, "API Key")

    T = tk.Text(frame, height=150, width=300, pady=20)
    T.pack()
    quote = """When selecting an Android application, please select the location of the \'activities\' folder. This location usually looks something like this: \'appname/app/src/main/java/com/example/username/project/activities\'."""
    T.configure(font=("Arial", 12, "bold"))
    T.insert(tk.END, quote)

    openDashboard = tk.Button(root, text="Open dashboard", padx=10, pady=10, fg="white", bg="#454545", command=openDashboard)
    openDashboard.pack()

    convertApp = tk.Button(root, text="Convert application", padx=10, pady=10, fg="white", bg="#454545", command=convertApp)
    convertApp.pack()

    root.mainloop()

# returns a list of all activities
def find_activities(activities_path):

    activities = os.listdir(activities_path)
    return activities

# returns a dict with activities as keys and direct connections as values
def find_connections(activities, activities_path):

    connections = {}

    for activity_name in activities:

        activity_connections = []
        
        with open('%s/%s' % (activities_path, activity_name), 'r') as f:
            
            # scan every line to look for connections
            for line in f:

                if 'new Intent' in line:

                    # find the activity that is being directed to
                    intent_start = line.find('new Intent')
                    connection_end = line.find('.class') # where name of activity that needs to be found ends
                    connection_start = line.find(',', intent_start)
                    connection_name = line[(connection_start + 1):(connection_end)].strip()

                    # TODO what if the activity is mentioned on the line below? (https://www.geeksforgeeks.org/string-find-python/) when it returns -1

                    if connection_name not in activity_connections:
                        activity_connections.append(connection_name)

        connections[activity_name.split('.')[0]] = activity_connections      

    return connections

# adds code to onCreate methods that keeps track of when a new activity is started
def add_oncreate_trackers(activities, activities_path, api_key, db_url):

    # add method that will keep track of usage
    tracking_method = '''
            final String activityName = this.getClass().getSimpleName();

            Thread thread = new Thread(new Runnable() {{

                @Override
                public void run() {{
                    try  {{
                        //Your code goes here
                        // Create URL
                        URL restdbEndpoint = null;
                        try {{
                            restdbEndpoint = new URL("{}");
                        }} catch (MalformedURLException e) {{
                            e.printStackTrace();
                        }}
                        // Create connection
                        HttpsURLConnection myConnection =
                                null;
                        try {{
                            myConnection = (HttpsURLConnection) restdbEndpoint.openConnection();
                        }} catch (IOException e) {{
                            e.printStackTrace();
                        }}
                        myConnection.setRequestProperty("User-Agent", "my-restdb-app");
                        myConnection.setRequestProperty("Accept", "application/json");
                        myConnection.setRequestProperty("x-apikey", "{}");

                        myConnection.setDoOutput(true);
                        Log.i("activityname", activityName);

                        String jsonInputString = String.format("%s", activityName);

                        try(OutputStream os = myConnection.getOutputStream()) {{
                            byte[] input = jsonInputString.getBytes("utf-8");
                            os.write(input, 0, input.length);
                            os.flush();

                        }} catch (IOException e) {{
                            e.printStackTrace();
                        }}

                        try {{
                            if (myConnection.getResponseCode() == 200) {{
                                // Success
                                // Further processing here
                            }} else {{
                                // Error handling code goes here
                                Log.i("RESPONSE CODE", Integer.toString(myConnection.getResponseCode()));
                            }}
                        }} catch (IOException e) {{
                            e.printStackTrace();
                        }}
                    }} catch (Exception e) {{
                        e.printStackTrace();
                    }}
                }}
            }});

            thread.start();
    '''.format(db_url, api_key)
    
    for activity_name in activities:

        dummy_file = '%s/%s' % (activities_path, 'dummy_file.java')
        original_file = '%s/%s' % (activities_path, activity_name)

        on_resume_found = False
        on_resume_added = False

        # open original file in read mode and dummy file in write mode
        with open(original_file, 'r') as read_obj, open(dummy_file, 'w') as write_obj:

            line_count = 1

            # Read lines from original file one by one and append them to the dummy file
            for line in read_obj:

                if line_count == 2:

                    '''
                    Write necessary imports here!
                    '''
                    write_obj.write('import android.util.Log;' + '\n')
                    write_obj.write('import java.net.URL;' + '\n')
                    write_obj.write('import javax.net.ssl.HttpsURLConnection;' + '\n')
                    write_obj.write('import java.net.MalformedURLException;' + '\n')
                    write_obj.write('import java.io.IOException;' + '\n')
                    write_obj.write('import com.android.volley.toolbox.HttpResponse;' + '\n')
                    write_obj.write('import java.io.OutputStream;' + '\n')

                elif 'onCreate' in line and 'super.onCreate' not in line:

                    write_obj.write(line)

                    write_obj.write(tracking_method + '\n')

                elif 'onResume' in line and 'super.onResume' not in line and on_resume_added == False:
                    write_obj.write(line)
                    on_resume_found = True
                    
                elif on_resume_found == True and on_resume_added == False:

                    if 'super.onResume' in line:
                        write_obj.write(line)
                        write_obj.write(tracking_method + '\n')
                    else:
                        write_obj.write(tracking_method + '\n')
                        write_obj.write(line)

                    on_resume_added = True

                else:
                    write_obj.write(line)

                line_count += 1

        # when activity does not have an onResume method yet
        if on_resume_added == False:
            with open(dummy_file, 'r') as read_obj, open('%s/%s' % (activities_path, 'dummy_file2.java'), 'w') as write_obj:

                for line in read_obj:

                    if 'public class %s' % activity_name.replace(".java", "") in line:
                        write_obj.write(line)

                        onresume_method ='''
        @Override
        public void onResume(){{
            super.onResume();
            {}
        }}
                        '''.format(tracking_method)

                        write_obj.write(onresume_method + '\n')
                    else:
                        write_obj.write(line)

            os.remove(original_file)
            os.remove(dummy_file)
            os.rename('%s/%s' % (activities_path, 'dummy_file2.java'), original_file)

        else:
            os.remove(original_file)
            os.rename(dummy_file, original_file)
        
    print("Application successfully converted")    

# makes sure the application is able to connect to the internet
def enable_internet_access(activities_path):

    # the number 7 here is based on the length of the 'scripts' folder name
    dummy_file = activities_path[0:activities_path.find("main", 0, len(activities_path))+5] + 'dummy_file.xml'
    original_file = activities_path[0:activities_path.find("main", 0, len(activities_path))+5] + 'AndroidManifest.xml'

    permission_statement = '    <uses-permission android:name="android.permission.INTERNET" />'

    access_given = False

    # open original file in read mode and dummy file in write mode
    with open(original_file, 'r') as read_obj, open(dummy_file, 'w') as write_obj:

        access_given = False

        # Read lines from original file one by one and append them to the dummy file
        for line in read_obj:

            if 'android.permission.INTERNET' in line:
                access_given = True
                break

        if not access_given:
            
            # move back to top of file
            read_obj.seek(0)

            # indicates when the permission should be placed on the next line
            next_line = False

            permission_granted = False

            for line in read_obj:

                if 'package' in line and not permission_granted:

                    write_obj.write(line)
                    next_line = True

                elif not next_line:

                    write_obj.write(line)

                else:
                    write_obj.write(permission_statement + '\n')
                    next_line = False
                    permission_granted = True

            read_obj.close()
            write_obj.close()
            os.remove(original_file)
            os.rename(dummy_file, original_file)

        else:
            write_obj.close()
            os.remove(dummy_file)

# find the starting activity of the app
def find_main_activity(activities_path):

    # the number 7 here is based on the length of the 'scripts' folder name
    original_file = activities_path[0:activities_path.find("main", 0, len(activities_path))+5] + 'AndroidManifest.xml'

    # open original file in read mode and dummy file in write mode
    with open(original_file, 'r') as read_obj:

        activity_name = 'activity'

        for line in read_obj:

            if '<activity' in line:
                activity_line = read_obj.readline()
                activity_name = activity_line.split('.')

            if 'android:name="android.intent.action.MAIN"' in line:
                break

        read_obj.close()
        return activity_name[-1][0:-2]

# converts the list of connections to a JSON format with individual links and nodes
def convert_connections(connections, activities_path, links_amount):

    nodes = []
    links = []

    node_id = 1

    main_activity = find_main_activity(activities_path)

    for node in connections:

        if node == main_activity:
            main_bool = True

        else:
            main_bool = False

        # create node
        node_dict =	{
            "id": node,
            "name": node,
            "main": main_bool
        }

        nodes.append(node_dict)
        node_id += 1

        # create links
        for link in connections[node]:

            amount = links_amount.count('%s:%s' % (node, link))

            connection = {
                "source" : node,
                "target" : link,
                "amount" : amount
            }

            links.append(connection)

    converted_connections = {
        "nodes" : nodes,
        "links" : links
    }

    return converted_connections

# updates the amounts that links have been traveled based on real data
def get_links_amount(api_key, db_url):

    # make sure results are ordered based on id
    db_url += "?q={}&sort=_id"
    
    # get data from database
    headers = {
        'content-type': "application/json",
        'x-apikey': "%s" % api_key,
        'cache-control': "no-cache"
        }

    response = requests.request("GET", db_url, headers=headers)
    data = json.loads(response.text)

    activities = []

    first_activity = True
    
    for entry in data:
        
        # list out keys and values separately
        key_list = list(entry.keys()) 
        val_list = list(entry.values())
        activity = key_list[val_list.index("")]

        if first_activity == False:
            if activity == activities[-1]:
                pass
            else:
                activities.append(activity)
        else:
            activities.append(activity)
            first_activity = False

    links = []

    counter = 0

    for activity in activities:

        if counter != (len(activities) - 1):

            source = activity
            target = activities[counter + 1]

            links.append('%s:%s' % (source, target))

        counter += 1

    return links

# stores the connections in the visualisation/data folder as a JSON file
def store_connections(converted_connections):

    json_connections = json.dumps(converted_connections)

    f = open("../visualisation/data/data.json", "w")
    f.write(json_connections)
    f.close()

def run_server():

    PORT = 8000
    Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory='../visualisation')
    httpd = socketserver.TCPServer(("", PORT), Handler)
    webbrowser.open('http://localhost:%s' % PORT, new=2)
    print("serving at port", PORT)
    httpd.serve_forever()


def main():

    startGui()
    
    
if __name__ == '__main__':
    main()