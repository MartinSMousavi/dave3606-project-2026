# Mandatory project in DAVE3606

## Project overview

You have been hired by LEGO to work on their unfinished web application, improve their database structure, optimize queries, and make the server more robust and testable!

## Initial steps

1. Create a GitHub account if you don't already have one.

2. Form groups of two or three students. One group member must send the names, emails, and GitHub usernames of all the group members to one of the student assistants: Alexander Høyskel (alhoy1499@oslomet.no) or Nathaniel Bjerke-Kildal (s374923@oslomet.no).

3. In each project group, one member must _fork_ the project repository into their own GitHub account, and add the other member(s) as collaborators to the repository with write access. The forked repository is where you will collaborate. All the group members can then use `git clone` on their machine to obtain the forked repository. Note that the forked repository will be public; if you want a private repository, one group member can instead create a private GitHub repository, and then clone the official repository on their machine and run `git remote set-url origin git@github.com:username/repository` (replace `username` and `repository` with your actual username and repository name), and then `git push origin main`.


## Requirements
- Solve all the tasks below, and ensure that all the code is eventually committed to the master branch of your group's repository (though you should use other branches during development - in particular, you have to use a different branch for each Pull Request). There are some theory questions in the tasks; they may be answered either in the report (see below) or in code comments as you see fit.

- In general for all the tasks: take care not to introduce SQL injection vulnerabilities (Lecture 8) or [XSS vulnerabilities](https://en.wikipedia.org/wiki/Cross-site_scripting) (not covered, but this just amounts to always calling `html.escape()` on data from the database before inserting it into HTML).

- During the project, you should practice using code reviews in a collaborative development workflow. You must do at least the following:
    - Each group member must create and submit at least one Pull Request (PR) to the group's repository.
    - Each project member must review at least one PR that was submitted by another member of the group, and provide at least one request for change that must be performed by the PR author before the PR is merged. Not all suggestions have to be acted on - we encourage discussions about what the best approach for some problem is or what the most elegant code style is.

- The group must write a brief report (1-2 pages) where you briefly explain the choices you have made during development. Before the submission deadline, this needs to be committed to the repository as a file (if you're using Google Docs, please export the file as a PDF).

- All the code and the report need to be committed to your group's repository by the submission deadline, which is 23:59 on Friday March 27. By that time, you must also invite Alexander Høyskel, Nathaniel Bjerke-Kildal, and Åsmund Eldhuset as read-only collaborators to your group's repository - their GitHub usernames are `abh1abh`, `n8athaniel`, and `aasmundeldhuset`.

## Installation instructions

1. If you are on Windows: install WSL if you don't already have it.
1. Install Docker if you don't already have it, and start the Docker service if you haven't configured it to run automatically in the background. If you're on Linux, you might want to follow the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/) in order to avoid having to use `sudo` with every Docker command.
1. Install Python 3 if you don't already have it. Depending on how you install it, you might need to run `python3` instead of `python` in some of the commands below.
1. Install the Python dependencies [flask](https://pypi.org/project/Flask/) (a web server library) and [psycopg](https://pypi.org/project/psycopg/) (a PostgreSQL client library), which you can do by running `pip install -r requirements.txt` (possibly with `sudo`). If you get an error message saying that the system package manager wants to control the Pyhon libraries, try `sudo apt install python3-psycopg python3-flask`.
1. Run `./create_and_run_database.sh`, which will create and start a Docker container that runs a PostgreSQL database. If you shut down your machine, you can start the same database again with `./start_database_after_stopping.sh`. You can also stop the database with `./stop_database.sh`. At any time when the database is running, you can connect to it interactively with `./connect_to_database.sh` and run SQL queries. Use `\d` to see the list of tables, and e.g. `\d lego_set` to see the structure of a table. Type `exit` and press Enter to quit, or press Ctrl-D (Linux/Mac) or Ctrl-Z-Enter (Windows).
1. Run `python migrate_database.py`, which will create the necessary database tables.
1. [Download `bricklink.json.gz` from Canvas](https://oslomet.instructure.com/courses/33305/files/4556821/download) and place it into the directory where you cloned the repository (next to all the Python files).
1. Run `python import_into_database.py`, which will populate the database with data. This might take several minutes - the script regularly prints how many Lego sets it has inserted, and there are about 21000 sets. Do not run this script more than once - due to the initial lack of primary keys in the tables, that would cause duplicate data. If you need to reinsert the data, you can delete the existing rows in the database tables with `truncate table lego_inventory; truncate table lego_set; truncate table lego_brick;`.

### Running the web server

The starting point for this project is an unfinished web application located in `server.py`. Start the web server by running `python server.py`. This will print the URL on which the server is running - most likely [http://127.0.0.1:5000](http://127.0.0.1:5000). Go to that URL to see the list of all Lego sets.

# Tasks

## 1: Add database constraints
_[This is mainly about Lecture 8.]_

You notice that the database tables currently have no primary keys or foreign keys. Add appropriate primary keys and foreign keys to the database tables and explain your design choices briefly. In your report, show the SQL statements that you wrote to create the primary keys.

There are two ways to create the primary key for the `lego_brick` table, and six ways to create the primary key for the `lego_inventory` table. Given the column order that you chose, which kinds of queries will be sped up by your primary keys?

## 2: Design indexes for flexible queries
_[This is mainly about Lecture 8.]_

Your service needs to quickly answer questions like:
- Which LEGO sets contain a specific brick type, regardless of color?
- Which LEGO sets contain bricks of a specific color, regardless of type

Create the indexes that are needed to make these queries efficient (you might only need one index, if one of the primary keys you created in the previous task is enough to speed up one of these queries). Show the SQL statements for creating the indexes in the report. Before you execute the statements, use `\timing on` in the PostgreSQL client and run some queries that answer the kinds of questions that are shown above, and see how long they take. Create the indexes by executing the SQL statements in the PostgreSQL client. Run the queries again and see that they are faster now. Explain why the indexes you added improved the query performance.

## 3: Algorithmic complexity improvements
_[This is mainly about Lecture 2.]_

The endpoint handler for http://localhost:5000/sets is quite slow (several seconds).

Analyze the code. What time complexity does it have? Explain briefly in the report.

Improve the performance of the endpoint by using a more efficient approach to generate the HTML. (Note: the Python interpreter is in some situations able to detect the specific kind of performance problem that we have introduced in that endpoint handler and to automatically improve it. We have structured the Python code in a slightly odd way to prevent the interpreter from improving it. The solution to this task is _not_ to rely on the interpreter being clever - you should change the algorithm of the code in such a way that a good performance is guaranteed, even without the help of the interpreter.)

## 4. Encoding, compression, and file handle leaks
_[This is mainly about Lecture 6 and 7.]_

_Note: The original phrasing of this task was impossible to solve! Turns out UTF-32 is not supported by HTML 5, and it is not possible to directly specify in the response which byte order to use in UTF-16. The updated task description is now possible to implement. Sorry about that. Also note that it's not a good idea to use anything else than UTF-8 in HTML; this exercise is just to get something about encoding into this project._

Modify the endpoint handler for http://localhost:5000/sets to accept a query parameter that indicates the encoding in which the HTML response should be produced. The encodings that should be supported are `utf-16` and `utf-8` (this should be the default if the parameter is not given, or if the parameter specifies something else than these encodings). In addition to encoding the HTML string that the endpoint gives to Flask's `Response` constructor, you need to tell Flask to declare the encoding in a HTTP header, by adding `content_type=f"text/html; charset={encoding}"` as a parameter to Flask's `Response` constructor (with `encoding` set to the name of the encoding). Note that when calling `encode("utf-16")` on a Python string, you get little-endian UTF-16 with a byte order mark, and the browser will look at the byte order mark to determine the endianness - so you should not say `utf-16-le` or `utf-16-be` anywhere. If the encoding is not `utf-8`, you also need to delete the `<meta charset="UTF-8">` tag from the HTML template (you could turn this into a placeholder so that the endpoint handler can choose whether to have it there, similarly to how `{ROWS}` is used). Use the web browser's developer tools to inspect the `Content-Length` header in the responses, and see what effect the encoding has on the response size.

Compress the response using the [`gzip` library](https://docs.python.org/3/library/gzip.html#gzip.compress), and set the [Content-Encoding](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Encoding) response header to tell the browser how the response is compressed.

There are several file handle leaks in the server code: every time certain endpoints are requested, a file handle is created but not closed. Locate the problems and fix them, in such a way that the handle is closed even if reading the file fails in the middle.

## 5. File formats
_[This is mainly about Lecture 7.]_

Given a Lego set and its inventory, we want to be able to export it as a file in two different ways:

- The endpoint http://localhost:5000/api/set takes a Lego set id as a URL query parameter, and it should respond with the information about the set itself and its inventory, in the JSON format. Finish the implementation (the current implementation only responds with the set id). It is up to you to decide exactly how the JSON should be structured.

- Design your own binary file format for representing a Lego set and its inventory. Create an endpoint that takes a Lego set id as a URL query parameter and responds with a byte array that contains the data about the
Lego set in your format. (When you're sending the response, you need to specify `content_type="application/octet-stream"`.) Describe the file format in the report.

Write a small console application in Python, Java, or C that is able to read such a binary file and print the information about the Lego set and its inventory.

## 6: Frontend and caching
_[This is mainly about Lecture 9.]_

Finish the implementation of the frontend code for http://localhost:5000/set (the JavaScript code in `templates/set.html`), which should show a detailed view of a Lego set and its inventory (the bricks that it consists of). The JavaScript in the HTML page already calls the JSON endpoint from the previous task. Populate the page based on the JSON data. (If you want to get fancy in a way that is not related to the course, you can use a JavaScript frontend library like React or Vue and an accompanying build system. But the task can be solved by writing plain JavaScript that directly manipulates the Document Object Model to dynamically modify the HTML of the page.)

Add a server-side cache that stores the 100 most recently requested sets. Cache entries should include both the set and its bricks. The endpoint should:
- Return cached result if available.
- Query the database only on cache misses, and update the cache with the result.
- Use a well-known eviction policy for deciding which cache entry to remove when the cache has become full and we need to insert another entry. The eviction policy must be implemented efficiently, so that if there are _n_ elements in the cache, it must take at most _O_(lg _n_) operations to evict an item (but some eviction policies can be implemented in _O_(1)).

Explain briefly in the report how the cache works, which eviction policy you chose, and what its complexity is. Measure how much time the endpoint spends when the set inventory is cached vs. when it is not.

Add an appropriate `Cache-Control` header to the response from http://localhost:5000/sets to make the browser cache the page for up to one minute. Reload the page a few times and see that only the first load is slow, and that subsequent loads within one minute are fast and do not result in a request to the server.

## 7: Testing and dependency injection
_[This is mainly about Lecture 10 and 11.]_

The server code currently uses a global database connection, which makes the code difficult to test. Refactor all the endpoint handlers that use the database by splitting most of the endpoint code out into a separate function. The only things that should happen in the endpoint handler itself is to read the URL query parameter if necessary, and to pass it as a parameter to the separate function; the separate function should return the result as a string that contains HTML or JSON, and the endpoint handler should wrap it in a `Response` with the appropriate content type and return it.

Then, create a class `Database` that serves as wrapper for the `psycopg` database library. It should have a function called `execute_and_fetch_all` that does the following:
- Takes an SQL query as a parameter.
- Creates a connection and a "cursor" using `psycopg` (in the same way that the existing code does, but without using `with`) and stores them as member properties on the object/
- Calls `execute` on the cursor with the given query, and returns the result of calling `fetchall` on the cursor afterwards.

The `Database` class should also have a `close` function that closes the cursor and the connection.

Instead of using `psycopg` directly in the separate endpoint functions, an instance of the `Database` class should be created in the endpoint handler and passed to the function, so that that function only needs to call `execute_and_fetch_all` and `close` on the `Database` instance.

Write a test for each of the separate endpoint functions. In each test, create a mock of the `Database` class, which checks that the SQL query that it is asked to perform is the expected query for that endpoint, and responds with a small number of "SQL rows". Assert that the resulting HTML or JSON from the endpoint is correct given the mocked "query result".
