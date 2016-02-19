## Flask setup
Install python-pip on your machine and then use pip to install flask.

[pip installation link](https://pip.pypa.io/en/stable/installing/)

[flask installation link](http://flask.pocoo.org/docs/0.10/installation/)

## How to use settings_template.ini
Copy the template to settings.ini and then fill the fields required in that file.

`bash$ cp settings_template.ini settings.ini`

## Running the server
By default, the server listens on 0.0.0.0 port 9999. If you want to change it 
to custom ip and port, you can modify those values in endpoint.pp or can provide
it as input arguments to the script by modifying it to read input arguments.

`bash$ python endpoint.py`

## Hacks done
As of on [02/18/16], we found that registry v2 was not returning us the tag of 
the image. We needed to find which image is recently added/updated along with
the tag. To do this, we took a workaround:-

1. We parsed the notifications and looked for "push" of manifests.
2. We retrieved the image name and then pulled manifest associated with it using
the url we received in the notification.
3. We then parsed all the digests that image is composed of and stored them.
4. Then, based on the image name obtained, we fetched all the tags associated 
with that particular image. 
5. Next, we downloaded the manifest for each image and tag, looked through each
manifest and fetched all the digests contained by it. If all the digests matches
with the earlier fetched digests till step 3, we say that this tag is the newly
added/modified tag.

**NOTE:** The drawback of this approach is that if two images have no difference
in them, like v3 is exact copy of v2, then it will always refer to one of the
tag only even though you might have pushed the image with different tag name.

## Useful links:-
[Information about docker manifests](https://docs.docker.com/registry/spec/api/#manifest)

[Docker manifest versions v1 and v2](https://github.com/docker/docker/issues/8093)

[Github link to docker registry v1 and v2](https://github.com/docker/distribution/blob/master/docs/spec/api.md)

## Important bugs:-
[add digest info to v2 registry tags list](https://github.com/docker/docker/issues/14082)
