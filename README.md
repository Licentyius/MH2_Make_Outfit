# MH2_Make_Outfit

MH2 Official Integrated Style Plugin- Make Outfit.  This is the first of the official integrated  plugins to be available for testing purposes.
This is an evolving plugin for simply saving outfits in a wardrobe style way.

Integrated/official plugin example in mh2_official_tools(folder structure map):
**note this is not the same as the drop in extension style plugins).

# Folder Structure for the integrated plugins for makehuman 2:

makehuman2/
├── pyproject.toml
├── extensions/                    <-- (Leave empty for community drop-ins)
└── mh2_official_tools/            <-- Core plugin package
        ├── __init__.py            <-- Main gateway entry point
        ├── small tool_alpha.py
        ├── small tool_beta.py
        └── Large_cool_tool/        <-- Multi-file tool subfolder
            ├── __init__.py         <-- Sub-tool entry point
            ├── tool_alpha.py
            ├── manifest.toml
            ├── data/
            │   └── resource.json
            └── core/
                └── functional.py


.json saved outfit presets can be saved, exported and shared. The presets load onto the screen with a double click.

~>Please be aware this is not a stand-alone tool, it requires Makehuman 2 in order to load, to use this you install it in the mh2_official_tools folder,
First open up makehuman 2, then pull down the community plugins menu in mh2(settings-community plugins), you should see the plugin panel open up to
allow any installed extensions and plugins to be used. Enable the plugin. At present this should open it right up as a fully dockable window of its own.




