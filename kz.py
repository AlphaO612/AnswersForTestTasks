class Connection(typing.ContextManager):
    def execute(self, query: str, params: tuple):
        print("Executed query", query, params)
    
    def commit(self):
        pass
    def close(self):
        pass


class DbManager:
    def open_connection(self) -> "Connection":
        return Connection()

"""
ISSUES:
    - Use `.fetchone()` with `[0]`, but in the query, you're trying to call all rows, 
    and then only take one after executing a query in the DB. 
    That is the issue because the query is trying to fetch all rows, which slows down the execution of the code.
    SOLUTION: 
        If you need only one, use the `LIMIT` clause in the `SELECT` command to limit the number of rows returned by the query. 
        If only one is needed, add this to the query. This solution could make the execution of methods faster.
        . . . and I'm not sure, because I don't know the documentation for this module, but:
        If you use `.fetchone()`, after executing and fetching the result, you should expect
        just a single value like an int, str, etc., in most modules, not a tuple, list, or set.
        That is why I removed `[0]` after `.fetchone()` everywhere.

    - Every method needs `employee_id` as input parameters.
    - Every time some methods are called, a new `dbManager` is created, and a connection is opened without closing it, 
    which can cause issues due to multiple open connections.
    SOLUTION:
        We see that every method expects an `employee_id` in the input parameters, and every time a `dbManager` is initialized 
        and a connection is opened.
        First step, make the `dbManager` accessor from local to static protected.
        Second step, open a connection only when necessary. 
        Comment: Every method in `WorkingHourManage` needs for single execution query, not multiple. 
            This makes it a bit different. You will need to open the connection before the method execution and close it afterward.
            If this is accurate, consider a second version of fixing this code using a decorator.
        Third and final step, add a protected `employee_id` to the object, and have all methods link to this object's value.

    - Executing two different queries to make one calculation only for one.
    SOLUTION:
        Just make a single query and execute only that one.

    - Performing calculations after solving issues.
    SOLUTION:
        This isn't necessarily an issue, just a slightly strange idea, because you can do these calculations within the query itself.

     
"""

# ------------------ FIRST VER ------------------ 
class WorkingHourManager: # if this needs to use so many times, this solution is a good idea to use
    _db_manager = DbManager()

    def __init__(self, employee_id: int):
        self._connection = self._db_manager.open_connection()
        self._employee_id = employee_id
    
    @property
    def employee_id(self) -> int:
        return self._employee_id
    
    def log(self, time) -> None:
        print("Logged working hours", time)
        self._connection.execute(
            "INSERT INTO working_log (employee_id, time) VALUES (?, ?)",
            (
                self.employee_id,
                time,
            ),
        )

    def total(self):
        return (
            self._connection.execute(
                "SELECT SUM(time_in_seconds)*60*60 FROM working_log WHERE employee_id = ? LIMIT 1",
                (self.employee_id,),
            ).fetchone()
        )

    def salary(self, date_from: str, date_to: str):

        total_time, hour_rate = self._connection.execute(
            (
                "SELECT X.sum, Y.hour_rate"
                "FROM (SELECT sum(time_in_seconds) as 'sum' FROM working_log "
                    "WHERE employee_id = ? and time_in_seconds >= ? and time_in_seconds <= ?"
                    "LIMIT 1"
                ") as X, (SELECT hour_rate as 'hour_rate' FROM employee_rates WHERE employee_id = ? LIMIT 1) as Y"
            ),
            (
                self.employee_id,
                date_from,
                date_to,
                self.employee_id,
            ),
        ).fetchone()

        return total_time * hour_rate


# ------------------ SECOND VER ------------------ 
class WorkingHourManager: # if this needs to use not so often, this solution is a good idea to use
    _db_manager = DbManager()

    @staticmethod
    def prepare_connection(func):
        def wrapped(*args, **kwargs):
            obj = args[0]
            obj.connection = obj._db_manager.open_connection()
            result = func(*args, **kwargs)
            obj.connection.commit()
            obj.connection.close()
            return result
        return wrapped

    def __init__(self, employee_id: int):
        # self.connection = self._db_manager.open_connection() - transfered to decorator
        self.connection = None
        self._employee_id = employee_id
    
    @property
    def employee_id(self) -> int:
        return self._employee_id

    @prepare_connection
    def log(self, time) -> None:
        print("Logged working hours", time)
        self.connection.execute(
            "INSERT INTO working_log (employee_id, time) VALUES (?, ?)",
            (
                self.employee_id,
                time,
            ),
        )

    @prepare_connection
    def total(self):
        return (
            self.connection.execute(
                "SELECT SUM(time_in_seconds)*60*60 FROM working_log WHERE employee_id = ? LIMIT 1",
                (self.employee_id,),
            ).fetchone()
        )

    @prepare_connection
    def salary(self, date_from: str, date_to: str):
        total_time, hour_rate = self.connection.execute(
            (
                "SELECT X.sum, Y.hour_rate"
                "FROM (SELECT sum(time_in_seconds) as 'sum' FROM working_log "
                    "WHERE employee_id = ? and time_in_seconds >= ? and time_in_seconds <= ?"
                    "LIMIT 1"
                ") as X, (SELECT hour_rate as 'hour_rate' FROM employee_rates WHERE employee_id = ? LIMIT 1) as Y"
            ),
            (
                self.employee_id,
                date_from,
                date_to,
                self.employee_id,
            ),
        ).fetchone()

        return total_time * hour_rate
