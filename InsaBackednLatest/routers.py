# my_project/routers.py


class ReplicationRouter:
    """
    A database router that sends read queries to the replica database and
    write queries to the master database.
    """

    def db_for_read(self, model, **hints):
        print("here is the db_for_read")
        return "replica"  # Read from the replica

    def db_for_write(self, model, **hints):
        print("here is the db_for_write")
        return "default"  # Write to the master

    def allow_relation(self, obj1, obj2, **hints):
        print("here is the allow_relation")
        return True  # Allow relations between models

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        print("here is the allow_migrate")
        return db == "default"  # Migrations should only run on the default (master) DB
