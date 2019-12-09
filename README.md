# Qtazu

Python Qt widgets for [CG-Wire](https://www.cg-wire.com/) using [`gazu`](https://github.com/cgwire/gazu).

#### Dependencies

This requires [Gazu](https://github.com/cgwire/gazu) and [Qt.py](https://github.com/mottosso/Qt.py).

## What is Qtazu?

*Qtazu* implements Qt widgets that can be reused across projects to connect and work with a CG-Wire instance through an interface running in Python.

These widgets can then be embedded in DCCs like Maya, Houdini or even standalone Python applications like a studio pipeline.

**WIP**: *This is a WIP repository*

## Usage Examples

The Widgets are implemented in such a way you can easily initialize them as you need. 

Here are some examples:

_The examples assume a running Qt application instance._

**Logging in**

```python
from qtazu.widgets.login import Login

widget = Login()
widget.show()
```

If you want to set your CG-Wire instance URL so the User doesn't have to you can set it through environment variable: `CGWIRE_HOST`

```python
from qtazu.widgets.login import Login
import os

os.environ["CGWIRE_HOST"] = "https://zou-server-url/api"
widget = Login()
widget.show()
```

Or you can automate a [login through `gazu`](https://github.com/cgwire/gazu#quickstart) and `qtazu` will use it.
Or if you have logged in through another Python process you can pass on the tokens:

```python
import os
import json

# Store CGWIRE_TOKENS for application (simplified for example)
os.environ["CGWIRE_TOKENS"] = json.dumps(gazu.client.tokens)
os.environ["CGWIRE_HOST"] = host


# In application "log-in" using the tokens
host = os.environ["CGWIRE_HOST"]
tokens = json.loads(os.environ["CGWIRE_TOKENS"])
gazu.client.set_host(host)
gazu.client.set_tokens(tokens)
```

**Submitting Comments**

You can easily submit comments for a specific Task, this includes drag 'n' dropping your own images of videos as attachment or using a Screen Marguee tool to attach a screenshot to your comment.

_Make sure you are logged in prior to this._

```python
from qtazu.widgets.comment import CommentWidget

task_id = "xyz" # Make sure to get a valid Task Id for your instance
widget = CommentWidget(task_id=task_id)
widget.show()
```

**Display all Persons with Thumbnails**

```python
from qtazu.models.persons import PersonModel
from Qt import QtWidgets, QtCore

model = PersonModel()
view = QtWidgets.QListView()
view.setIconSize(QtCore.QSize(30, 30))
view.setStyleSheet("QListView::item { margin: 3px; padding: 3px;}")
view.setModel(model)
view.setMinimumHeight(60)
view.setWindowTitle("CG-Wire Persons")
view.show()
```

**Define your own Qt widget that loads Thumbnails in the background**

This will show all CG-Wire projects as thumbnails

```python
import gazu
from Qt import QtWidgets
from qtazu.widgets.thumbnail import ThumbnailBase

main = QtWidgets.QWidget()
main.setWindowTitle("CG-Wire Projects")
layout = QtWidgets.QHBoxLayout(main)

for project in gazu.project.all_open_projects():
   
    thumbnail = ThumbnailBase()
    thumbnail.setFixedWidth(75)
    thumbnail.setFixedHeight(75)
    thumbnail.setToolTip(project["name"])
    project_id = project["id"]
    thumbnail.load("pictures/thumbnails/projects/{0}.png".format(project_id))
    layout.addWidget(thumbnail)
    
main.show()
```

**Show a Welcome message to the logged in User**

```python
from Qt import QtWidgets, QtGui, QtCore
from qtazu.widgets.thumbnail import ThumbnailBase
import gazu


class UserPopup(QtWidgets.QWidget):
    """Pop-up showing 'welcome user' and user thumbnail"""
    def __init__(self, parent=None, user=None):
        super(UserPopup, self).__init__(parent=parent)
    
        layout = QtWidgets.QHBoxLayout(self)
   
        thumbnail = ThumbnailBase()
        thumbnail.setFixedWidth(75)
        thumbnail.setFixedHeight(75)
        thumbnail.setToolTip(user["first_name"])
        
        welcome = QtWidgets.QLabel("Welcome!")
        
        layout.addWidget(thumbnail)
        layout.addWidget(welcome)
    
        self.thumbnail = thumbnail
        self.welcome = welcome
        self._user = None
        
        if user:
            self.set_user(user)
    
    def set_user(self, user):
        
        self._user = user
        
        # Load user thumbnail 
        self.thumbnail.load("pictures/thumbnails/persons/{0}.png".format(user["id"]))
        
        # Set welcome message
        self.welcome.setText("Welcome {first_name} {last_name}!".format(
            **user
        ))


# Show pop-up about current user
user = gazu.client.get_current_user()
popup = UserPopup(user=user)
popup.show()
```
