# Gravitty

Gravitty is my captstone project for Zipfian Academy. Its aim is to detect latent, behavior-driven communities in a twitter user's followers.

### Why's this useful? 

Brands want to know their audience. The market for follower analytics today is crowded with companies that, for the most part, either analyze followers en masse or look to the most influencial amplifiers.

Looking to communities of followers allows us to see what groups of like-minded followers are talking about and who they're talking about it to.

### Can I see it?

Please do. Check it out [here](http://gravitty.ericjeske.com)

Unfortunately it can take a while to collect, process, & analyze all of this data, so at the moment the site relies on pre-cached examples.

Eventually I'll add a real-time search for users with small amounts of followers and a time-lagged search feature for users with larger follower bases.


## "Quick" Install:

Installing this isn't as trivial as I'd like -- it's still a prototype! There's a few things you'll need to do to get going after you've cloned:

### Twitter:
 - Go to dev.twitter.com and make an application. Copy the api keys and tokens (four lines total) into a text document (name doesn't matter).
 - Save this text document in a folder called 'api_keys' in the gravitty subfolder. You may have to create the folder.
 - One api-key = 15 requests per 15 minutes. Which means 15 followers per 15 minutes... So think about repeating steps 1 and 2 a few times, just remember to save each set of api keys into a new file.

### Mongo:
 - Given the rate limit issues described above, I highly recommend (to the point of making it mandatory) that you run a mongo database to cache user data.
 - Run `mongod` before using gravitty. By default, gravitty stores cached data into a database called twitter and a collection called data, both of which will be created dynamically on its first run.
 - Optinal Pro tip: if you mongo database gets big, I highly recommend changing the default index to be a compound index on id and type by running the command `db.data.ensureIndex({'id':1, 'type':1})` in the mongo console.

### Packages
 - first do: `easy_install https://github.com/mikedewar/d3py/tarball/master`
 - then do: `pip install -r requirements.txt`


## Usage

At the moment, there isn't a way to download new data through the web app (but it's on the todo list!). So you'll need to access the gravitty module directly:

```
import gravitty
screen_name = 'ericwjeske'
graph_json = gravitty.load('screen_name')
```

Be sure to exclude the '@' from the screen name!

You can check that the data is loaded by calling `gravitty.available()`, which should produce a list with all available, pre-cached users.

Once you've got some data loaded, launch the flask app to visualize the communities using d3.js:

```
python app.py 5000
```

and direct your browser to `0.0.0.0:5000`!

## Thanks!

If you find anything wrong -- from bugs to typos -- please send a message, write a comment, or send a pull request and I'll look into it.