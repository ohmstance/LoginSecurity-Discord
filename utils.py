import os

class ListFile:
    """Base class for inheritance, for tracking something in list, like Discord IDs. Saved to a file.
    """
    
    def __init__(self, filename):
        self.item_set = set()
        self.filename = filename
        self.reload(filename)
        
    def _contains(self, item):
        return str(item) in self.item_set
        
    def __contains__(self, item):
        return str(item) in self.item_set
                
    def _add(self, item):
        self.item_set.add(str(item))
        self.save()
        
    def _remove(self, item):
        self.item_set.remove(str(item))
        self.save()

    def reload(self, filename=None):
        filename = filename or self.filename
        
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                banstr = f.read().strip()
                if banstr:
                    self.item_set = set(banstr.split("\n"))
                
    def save(self, filename=None):
        filename = filename or self.filename
        
        with open(filename, "w") as f:
            for item in list(self.item_set):
                f.write(item+"\n")

    @property
    def _items(self):
        return list(self.item_set)
        
    def __repr__(self):
        return f"{self.__class__.__name__}(item_set={self.item_set})"
        
class BanFile(ListFile):
    """Class used for tracking banned Discord accounts, saved to a file.
    """
    
    def __init__(self, filename="banlist.txt"):
        super().__init__(filename)
        
    def is_banned(self, discord_id):
        return super()._contains(discord_id)
        
    def ban(self, discord_id):
        return super()._add(discord_id)
        
    def unban(self, discord_id):
        return super()._remove(discord_id)
        
    @property
    def banned(self):
        return super()._items
        
class AdminFile(ListFile):
    """Class used for tracking Discord accounts with admin permission, saved to a file.
    """
    
    def __init__(self, filename="adminlist.txt"):
        super().__init__(filename)
        
    def is_admin(self, discord_id):
        return super()._contains(discord_id)
        
    def promote(self, discord_id):
        return super()._add(discord_id)
        
    def demote(self, discord_id):
        return super()._remove(discord_id)
        
    @property
    def admins(self):
        return super()._items
        
class RegFile:
    """Simple class used to track if registrations are open or closed.
    """
    
    def __init__(self):
        self.filename = "server.closed"
        self.is_open = not os.path.isfile(self.filename)
        
    def close(self):
        with open(self.filename, "w") as f:
            pass
        self.is_open = False
        
    def open(self):
        if os.path.isfile(self.filename):
            os.remove(self.filename)
        self.is_open = True 
        
    def __repr__(self):
        return f"{self.__class__.__name__}(is_open={self.is_open})"
        