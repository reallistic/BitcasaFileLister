class BitcasaFile(object):
    def __init__(self, client, path, name, ext, size):
        self.client = client
        self.path = path
        self.name = name
        self.ext = ext
        self.size = size
        self.read_index = 0

    def __str__(self):
        return '<BitcasaFile name={f.name}, path={f.path}, size={f.size}>'.format(
                    f=self
                )

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def read(self):
        return self.client.get_file_contents(self.name, self.path)

    def delete(self):
        self.client.delete_file(self.path)

    def rename(self, new_name, exists='rename'):
        f = self.client.rename_file(self.path, new_name, exists)
        self.name = new_name
        return self

    def copy_to(self, folder, new_name=None, exists='rename'):
        if not new_name:
            new_name = self.name
        f = self.client.copy_file(self.path, folder.path, new_name, exists)
        return f

    def move_to(self, folder, new_name=None, exists='rename'):
        if not new_name:
            new_Name = self.name
        f = self.client.move_file(self.path, folder.path, new_name, exists)
        return f


class BitcasaFolder(object):
    def __init__(self, client, name, path, items=None):
        self.client = client
        self.name = name
        self.path = path
        self._items = items
        self._build_items()

    def _build_items(self):
        self._items_lookup = {item.name:index for index, item in enumerate(self._items if self._items else [])}

    @property
    def items(self):
        if self._items is None:
            self._refresh_items()
        return self._items

    def _refresh_items(self):
        folder = self.client.get_folder(self.path, self.name)
        self._items = folder._items if folder._items else []
        self._build_items()

    def __getitem__(self, key):
        if self._items is None:
            self._refresh_items()
        index = self._items_lookup[key]
        return self._items[index]

    def __str__(self):
        return '<BitcasaFolder name=%s, path=%s>' % (self.name, self.path)

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        for item in self.items:
            yield item

    def add_file(self, f, size, filename, exists='fail', refresh=True):
        self.client.upload_file(f, filename, self.path, exists)
        if refresh:
            self.refresh()
        return self

    def add_folder(self, name, refresh=True):
        folder = self.client.create_folder(self.path, name)
        if refresh:
            self.refresh()
        return self

    def refresh(self):
        folder = self.client.get_folder(self.path, self.name)
        self.name = folder.name
        self._items = folder._items if folder._items else []
        self._build_items()
        self.path = folder.path
        return self

    def delete(self):
        self.client.delete_folder(self.path)

    def rename(self, new_name, exists='rename'):
        folder = self.client.rename_folder(self.path, new_name, exists)
        self.name = new_name
        return self

    def copy_to(self, folder, new_name=None, exists='rename'):
        if not new_name:
            new_name = self.name
        folder = self.client.copy_folder(self.path, folder.path, new_name, exists)
        return folder

    def move_to(self, folder, new_name=None, exists='rename'):
        if not new_name:
            new_Name = self.name
        folder = self.client.move_folder(self.path, folder.path, new_name, exists)
        return folder

    @staticmethod
    def folder_from_response(client, name, path, result_items_list=None):
        items = None
        if result_items_list:
            items = []
            for result_item in result_items_list:
                if result_item['category'] == 'folders':
                    item = BitcasaFolder(
                            client,
                            result_item['name'],
                            result_item['path']
                        )
                else:
                    item = BitcasaFile(
                            client,
                            result_item['path'],
                            result_item['name'],
                            result_item['extension'],
                            result_item['size']
                        )
                items.append(item)
        return BitcasaFolder(client, name, path, items)
