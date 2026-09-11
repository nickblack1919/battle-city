# PyInstaller spec for Mac app "Battle City.app", build: ./build_app.sh

a = Analysis(
	["tanks.py"],
	datas=[("fonts", "fonts"), ("images", "images"), ("levels", "levels"), ("sounds", "sounds")],
	excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
	pyz,
	a.scripts,
	[],
	exclude_binaries=True,
	name="Battle City",
	console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Battle City")
app = BUNDLE(
	coll,
	name="Battle City.app",
	bundle_identifier="com.battlecity.game",
	info_plist={"NSHighResolutionCapable": True},
)
