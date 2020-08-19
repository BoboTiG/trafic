# Auto-Update Framework

This is a customized version of the [Nuxeo Drive auto-update framework](https://github.com/nuxeo/nuxeo-drive/tree/master/nxdrive/updater).

### Server

That version uses GitHub releases. No specific server is required.

### Client

For now, only Windows is handled.

Process:

1. At startup, if the `update` option is `False`, stop there;
2. Fetch relases using the GitHub API;
3. Find the latest version sorted by version;
4. Download the installer into a temporary folder.

Then, actions taken are OS-specific.

#### Windows

The only action to do is to install the new version by calling `trafic-x.y.z.exe /SILENT` from the temporary folder.
The installer will automagically:

1. Stop the application;
2. Install the new version, it will upgrade the old one without personal data loss;
3. Start the new version.

So, a big thank you to Inno Setup! Upgrade made so easy :)
