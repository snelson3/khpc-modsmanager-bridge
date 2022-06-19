import sys, os, shutil, subprocess, json, time, argparse
from gooey import Gooey, GooeyParser
from zipfile import ZipFile

# CLI usage example
#In [1]: import build_from_mm
#In [2]: build_from_mm.main(cli_args=["-game=kh2", "-mode=patch"])

# TODO 1.0.8 has new checksums for some of the packages, warn if on wrong checksomes

# TODO bundle as one file
# TODO support HD paths (DA: should be fine now)
# TODO bundle the pkgmap.json and pkgmap_extras.json as resources in the executable
# TODO add music only extract
# TODO blacklist bad directory paths, hide most output and make obvious errors more obvious (try to bulletproof it for non technical people)
# TODO make it a library
# TODO make a pypi package

VERBOSE_PRINTS = False

def print_debug(*args, **kwargs):
    verbose = "verbose" in kwargs and kwargs["verbose"]
    if (not verbose) or (verbose and VERBOSE_PRINTS):
        print(''.join([str(s) for s in args]))
    
class KingdomHearts1Patcher:
    def __init__(self, region):
        self.region = region
        self.name = "kh1"
        self.pkgs = ["kh1_first.pkg", "kh1_second.pkg", "kh1_third.pkg", "kh1_fourth.pkg", "kh1_fifth.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        return path
    def translate_pkg_path(self, path):
        return path

class KingdomHearts2Patcher:
    def __init__(self, region):
        self.region = region
        self.name = "kh2"
        self.pkgs = ["kh2_first.pkg", "kh2_second.pkg", "kh2_third.pkg", "kh2_fourth.pkg", "kh2_fifth.pkg", "kh2_sixth.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        #only translate paths that aren't in the raw or remastred folders
        #this is because those paths are always only used for the PC port
        if not path.startswith("remastered"+os.sep) or not path.startswith("raw"+os.sep):
            if os.sep+"jp"+os.sep in path:
                if not ".2ld" in path:
                    #check to see if the translated path already exists and ignore if it does
                    prepath = path.replace(os.sep+"jp"+os.sep, os.sep+self.region+os.sep)
                    PCverExists = os.path.isfile(moddir+os.sep+prepath)
                    if not PCverExists:
                        path = prepath
            if "ard" in path:
                if path.count(os.sep) == 1:
                    #check to see if the translated path already exists and ignore if it does
                    prepath = path.replace("ard"+os.sep, "ard"+os.sep+self.region+os.sep)
                    PCverExists = os.path.isfile(moddir+os.sep+prepath)
                    if not PCverExists:
                        path = prepath
            if "map" in path:
                if path.count(os.sep) == 2:
                #maps don't have region specifier for some reason, or they split it out into two files for some reason...
                    #check to see if the translated path already exists and ignore if it does
                    prepath = path.split("map")[0]+"map"+os.sep+path.split(os.sep)[-1]
                    PCverExists = os.path.isfile(moddir+os.sep+prepath)
                    if not PCverExists:
                        path = prepath
            if path.endswith(".a.fm"):
                #check to see if the translated path already exists and ignore if it does
                prepath = path.replace(".a.fm", ".a.{}".format(self.region))
                PCverExists = os.path.isfile(moddir+os.sep+prepath)
                if not PCverExists:
                    path = prepath
        return path
    def translate_pkg_path(self, path):
        return path

class BirthBySleepPatcher:
    def __init__(self, region):
        self.region = region
        self.name = "bbs"
        self.pkgs = ["bbs_first.pkg", "bbs_second.pkg", "bbs_third.pkg", "bbs_fourth.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        return path
    def translate_pkg_path(self, path):
        return path
class KingdomHearts3DPatcher:
    def __init__(self, region):
        self.region = region
        self.name = "kh3d"
        self.pkgs = ["kh3d_first.pkg", "kh3d_second.pkg", "kh3d_third.pkg", "kh3d_fourth.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        return path
    def translate_pkg_path(self, path):
        return os.path.join(path, "..", "..", "..", "KH_2.8", "Image", "en")

class RecomPatcher:
    def __init__(self, region):
        self.region = region
        self.name = "recom"
        self.pkgs = ["Recom.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        return path
    def translate_pkg_path(self, path):
        return path
class MoviesPatcher:
    def __init__(self, region):
        self.region = region
        self.name = "mare"
        self.pkgs = ["Mare.pkg"]
    def translate_path(self, path, moddir):
        if path.startswith(os.sep):
            path = path[1:]
        return path
    def translate_pkg_path(self, path):
        return os.path.join(path, "..")

games = {
    "kh1": KingdomHearts1Patcher,
    "kh2": KingdomHearts2Patcher,
    "bbs": BirthBySleepPatcher,
    "kh3d": KingdomHearts3DPatcher,
    "Recom": RecomPatcher,
    "Movies": MoviesPatcher
}
DEFAULTREGION = "us"
DEFAULTGAME = "kh2"
DEFAULTMODE = "patch"

old_checksums = {
    'kh2_first.pkg': 'b977794bb340dc6c7fad486940af48a4',
    'kh2_fourth.pkg': 'd0b7b1417ffc4cc7cec75a878b115adb',
    'kh2_second.pkg': '832454c68a676022c106364c30601927',
    'kh2_sixth.pkg': 'b9c31aa7a3296b9b62d875787baf757f',
    'kh2_third.pkg': '55ce51115dd0587deb504f57b34d1c6e', 
}

checksums = {
    'Recom.pkg': 'f05f21634ad3f14d1943abc16bb06183',
    'Theater.pkg': '1e08718a47d4aa0776931606e8fc9450',
    'bbs_first.pkg': 'c7623c0459d0b9bb7ba77e966f9d26bc',
    'bbs_fourth.pkg': 'c61f61dd5954d795c03ae17174c15944',
    'bbs_second.pkg': 'a45d032ac2e39637d4cdf54c67b58d1b',
    'bbs_third.pkg': '1eb46d47c521b4b7f127e3e71428cfa0',
    'kh1_fifth.pkg': 'c5527403cf2b8340bf943e916a2971bc',
    'kh1_first.pkg': '188acf5c53948e0dbfaf4d3a1b3a88c4',
    'kh1_fourth.pkg': '00830acd3599236b378208132dbbd538',
    'kh1_second.pkg': '7eb1206e1568448924fd9d7785f618ea',
    'kh1_third.pkg': '2489bdf1e8dbaddd2177bd35d9a4eefd',
    'kh2_fifth.pkg': '94ac4ced450ca269e95cc8f2769131cd',
    'kh2_first.pkg': '0d886ac09a61e5be53f08200a2f77282',
    'kh2_fourth.pkg': 'c87e2a1aa92bd6c68f473e6ed0fb8f76',
    'kh2_second.pkg': '815c71a09f2f0eb92985f91334f1beee',
    'kh2_sixth.pkg': 'f095b8f009e004a9d17a4c1ca948620d',
    'kh2_third.pkg': '48fbdf8354944abf557518ad2e67aa6c',
    'kh3d_first.pkg': 'dbf5819e8dbcd2377df7e5ff79f2cae7',
    'kh3d_fourth.pkg': '7ec4b89a5f9fe47b6f5fb046e710efcd',
    'kh3d_second.pkg': 'bb7fa91a01bc56a4307dad6f6769f1c1',
    'kh3d_third.pkg': 'c0f4bd34a14450956cd521842349cd24',
    'Mare.pkg': 'dbc743fef9e9bc7c974619e720082d18',

    'Recom.hed': '7722d36212d5ef9057ed47eda82b4a04',
    'Theater.hed': '3819742df5acd4f6dd80c204b69a73bd',
    'bbs_first.hed': '0b5858fd10ad296d7820bac05355d71d',
    'bbs_fourth.hed': '8e6f5b86ada09a7c5b00c4fd1642f857',
    'bbs_second.hed': 'e6d61ccc04fcba8ccc0e789ea53a8c02',
    'bbs_third.hed': '2ee77e135bb1823889f05ac13c1a9d8c',
    'kh1_fifth.hed': '4be388355d732c6f09d3c56fa6db7a2b',
    'kh1_first.hed': '1ac0102349a74db3c1eecf91bc284cb4',
    'kh1_fourth.hed': '0b14dda60f19fac1da50e20a408e50b8',
    'kh1_second.hed': 'c0b6b40c041542d5afd41357e02088f9',
    'kh1_third.hed': '4e799b35231269c525948a5815b6bcbf',
    'kh2_fifth.hed': '1091551eaf8281f249035180663b0a2e',
    'kh2_first.hed': '9a848ce98dc5808ded89f5fff2981f16',
    'kh2_fourth.hed': '53ee4061566a5700a3906b939fb4daed',
    'kh2_second.hed': 'c7020658f97efe251c50dfbca2c5a8dc',
    'kh2_sixth.hed': 'a3c87068d13b9a4dfe181c3bb907ac5e',
    'kh2_third.hed': '5865642b0826c55dbb143dc843adef74',
    'kh3d_first.hed': '83892d2534c98c3b50d7aaaaf9d51889',
    'kh3d_fourth.hed': '55ee6fbd6a025fa62bdfeb9243876202',
    'kh3d_second.hed': '135baeac7ce2e36e52b4fbb72d7e056b',
    'kh3d_third.hed': '71792c53ec9584198e60378a4df52a86',
    'Mare.hed': 'f5d4a45e048f586ecbf1a71f43e8dafd'
}

import hashlib 

def validChecksum(path):
    pkgname = path.split(os.sep)[-1]
    if pkgname not in checksums:
        raise Exception("Error: Checksum for {} not found!".format(pkgname))
    checksum = hashlib.md5(open(path,'rb').read()).hexdigest()
    if not checksum == checksums[pkgname]:
        print_debug("PKG {} has changed checksum!".format(pkgname))
        return False
    return True

@Gooey(program_name="Mod Manager Bridge")
def main_ui():
    main()

def main(cli_args: list = []):
    starttime = time.time()

    default_config = {
        "game": DEFAULTGAME,
        "mode": DEFAULTMODE,
        "openkh_path": "",
        "extracted_games_path": "",
        "khgame_path": "",
        "region": DEFAULTREGION,
        "patches_path": ""
    }
    if os.path.exists("config.json"):
        default_config = json.load(open("config.json"))

    parser = GooeyParser()

    main_options = parser.add_argument_group(
        "Main options",
        "The main options around the mode and game to use. All required"
    )
    
    #fallback measure for backwards compalibility with the old config.json
    getmode = DEFAULTMODE
    if default_config.get("mode") is not None:
        if "fast" in default_config.get("mode"):
            getmode = "fast_patch"

    main_options.add_argument("-game", choices=list(games.keys()), default=default_config.get("game"), help="Which game to operate on.", required=True)
    main_options.add_argument("-mode", choices=["extract", "patch", "restore", "fast_patch", "fast_restore"], default=getmode, help="Which mode to run (`Patch` patches the game, `Extract` extracts the pkg files for the game, and `Restore` will restore the backed up pkg files without patching anything)", required=True)
    #removed `uk` from region choices. uk just uses us for everything anyway aside from some journal stuff so it's not worth using ever and causes confusion in my opinion.
    main_options.add_argument("-region", choices=["jp", "us", "it", "sp", "gr", "fr"], default=default_config.get("region", ""), help="defaults to 'us', needed to make sure the correct files are patched")


    main_options = parser.add_argument_group(
        "Setup",
        "Paths that must be configured to make sure the patcher works properly."
    )
    main_options.add_argument("-openkh_path", help="Path to OpenKH folder.", default=default_config.get("openkh_path"), widget='DirChooser')
    main_options.add_argument("-extracted_games_path", help="Path to folder containing extracted games", default=default_config.get("extracted_games_path"), widget='DirChooser')
    main_options.add_argument("-khgame_path", help="Path to the Kingdom Hearts game install directory.", default=default_config.get("khgame_path"), widget='DirChooser')
    main_options.add_argument("-patches_path", help="(Optional) Path to directory containing other kh2pcpatches to apply. Will be applied in alphabetical order (Mods Manager mods will be applied last).", default=default_config.get("patches_path"), widget='DirChooser')


    advanced_options = parser.add_argument_group(
        "Advanced Options",
        "Development options for the most part, if you don't know what these do then leave them alone."
    )
    advanced_options.add_argument("-keepkhbuild", action="store_true", default=False, help="Will keep the intermediate khbuild folder from being deleted after the patch is applied")
    advanced_options.add_argument("-ignorebadchecksum", action="store_true", default=False, help="If true, disabled backing up and restoring the original PKG files based on checksums (you probably don't want to check this option)")
    advanced_options.add_argument('-failonmissing', action="store_true", default=False, help="If true, fails when a file can't be patched to a PKG, rather than printing a warning")
    
    # Parse and print the results
    if cli_args:
        args = parser.parse_args(cli_args)
    else:
        args = parser.parse_args()

    config_to_write = {
        "game": args.game,
        "mode": args.mode,
        "openkh_path": args.openkh_path,
        "extracted_games_path": args.extracted_games_path,
        "khgame_path": args.khgame_path,
        "region": args.region,
        "patches_path": args.patches_path,
    }
    json.dump(config_to_write, open("config.json", "w"))

    MODDIR = os.path.join(args.openkh_path, "mod")
    IDXDIR = args.openkh_path
    IDXPATH = os.path.join(IDXDIR, "OpenKh.Command.IdxImg.exe")

    gamename = args.game
    if not args.game in games:
        raise Exception("Game not found, possible options: {}".format(list(games.keys())))
    region = args.region
    game = games[gamename](region=region)

    PKGDIR = game.translate_pkg_path(os.path.join(args.khgame_path, "Image", "en"))

    if not os.path.exists(PKGDIR):
        raise Exception("PKG dir not found")
    if not os.path.exists(IDXPATH):
        raise Exception("OpenKh.Command.IdxImg.exe not found")

    mode = args.mode
    patch = True if mode in ["patch", "fast_patch"] else False
    fastpatch = True if mode == "fast_patch" else False
    extract = True if mode == "extract" else False

    extra_patches_dir = args.patches_path or ''

    keepkhbuild = args.keepkhbuild
    validate_checksum = args.ignorebadchecksum
    ignoremissing = not args.failonmissing

    backup = True if mode in ["patch", "fast_patch"] else False
    restore = True if mode in ["patch", "restore", "fast_patch", "fast_restore"] else False
    fastrestore = True if mode in ["fast_patch", "fast_restore"] else False

    pkgmap = json.load(open("pkgmap.json")).get(game.name, {})
    pkgmap_extras = json.load(open("pkgmap_extras.json")).get(game.name, {}) # predefined extras for patches that fail otherwise, such as GOA ROM
    pkgmap_blacklist = json.load(open("pkgmap_blacklist.json")).get(game.name, {}) # blacklist of bad files to replace
    pkgmap.update(pkgmap_extras)

    if extract:
        print_debug("Extracting {}".format(game.name))
        if not os.path.exists(args.extracted_games_path):
            raise Exception("Path does not exist to extract games to! {}".format(args.extracted_games_path))
        print(game.name)
        pkglist = [os.path.join(PKGDIR,p) for p in os.listdir(PKGDIR) if game.name.lower() in p.lower() and p.endswith(".hed")]
        if os.path.exists("extractedout"):
            shutil.rmtree("extractedout")
        os.makedirs("extractedout")
        EXTRACTED_GAME_PATH = os.path.join(args.extracted_games_path, game.name)
        if EXTRACTED_GAME_PATH.endswith("kh3d"):
            EXTRACTED_GAME_PATH = EXTRACTED_GAME_PATH.replace("kh3d", "ddd")
        print(EXTRACTED_GAME_PATH)
        if os.path.exists(EXTRACTED_GAME_PATH):
            shutil.rmtree(EXTRACTED_GAME_PATH)
        print_debug(pkglist, verbose=True)
        for pkgfile in pkglist:
            if not validChecksum(pkgfile[:-4]+".pkg") and validate_checksum:
                raise Exception("Error: {} has an invalid checksum, please restore the original file!".format(pkgfile))
            idx_args = [IDXPATH, "hed", "extract", pkgfile, "-o", "extractedout"]
            print_debug(IDXPATH, "hed", "extract", '"{}"'.format(pkgfile), "-o", '"{}"'.format("extractedout"))
            try:
                output = subprocess.check_output(idx_args, stderr=subprocess.STDOUT)
                print_debug(output, verbose=True)
            except subprocess.CalledProcessError as err:
                output = err.output
                print_debug(output.decode('utf-8'))
                raise Exception("Extract failed")
        original_path = os.path.join("extractedout", "original")
        remastered_path = os.path.join("extractedout", "remastered")
        if os.path.exists(remastered_path):
            shutil.move(remastered_path, os.path.join(original_path, "remastered"))
        shutil.move(original_path, args.extracted_games_path)
        os.rename(os.path.join(args.extracted_games_path, "original"), EXTRACTED_GAME_PATH)
    if backup:
        if not os.path.exists("backup_pkgs"):
            os.makedirs("backup_pkgs")
        for pkg in game.pkgs:
            sourcefn = os.path.join(PKGDIR, pkg)
            newfn = os.path.join("backup_pkgs", pkg)
            if not os.path.exists(newfn):
                print_debug("Backing up file: " + sourcefn)
                if not validChecksum(sourcefn) and validate_checksum :
                    raise Exception("Error: {} has an invalid checksum, please restore the original file and try again".format(sourcefn))
                shutil.copy(sourcefn, newfn)
                shutil.copy(sourcefn.split(".pkg")[0]+".hed", newfn.split(".pkg")[0]+".hed")
    if restore:
        print_debug("Restoring from backup")
        if not os.path.exists("backup_pkgs"):
            raise Exception("Backup folder doesn't exist")
        if fastrestore:
            if gamename != "Recom" or gamename != "Movies":
                pkgname = gamename + "_first.pkg"
                newfn = os.path.join(PKGDIR, pkgname)
                sourcefn = os.path.join("backup_pkgs", pkgname)
                if validChecksum(newfn.split(".pkg")[0]+".hed"):
                    pass
                else:
                    print("Restoring {}".format(pkgname))
                    shutil.copy(sourcefn, newfn)
                    shutil.copy(sourcefn.split(".pkg")[0]+".hed", newfn.split(".pkg")[0]+".hed")
        else:
            for pkg in game.pkgs:
                newfn = os.path.join(PKGDIR, pkg)
                sourcefn = os.path.join("backup_pkgs", pkg)
                if validChecksum(newfn.split(".pkg")[0]+".hed"):
                    continue
                else:
                    print("Restoring {}".format(pkg))
                    shutil.copy(sourcefn, newfn)
                    shutil.copy(sourcefn.split(".pkg")[0]+".hed", newfn.split(".pkg")[0]+".hed")
    if patch:
        print_debug("Patching")
        if os.path.exists("khbuild"):
            shutil.rmtree("khbuild")
        os.makedirs("khbuild")
        if os.path.exists(MODDIR):
            for root, dirs, files in os.walk(MODDIR):
                path = root.split(os.sep)
                for file in files:
                    fn = os.path.join(root, file)
                    relfn = fn.replace(MODDIR, '')
                    relfn_trans = game.translate_path(relfn, MODDIR)
                    print_debug("Translated Filename: {}".format(relfn_trans), verbose=True)
                    #raw paths are the exact same as original paths, just with the root flder being "raw" instead of "original"
                    #so we can check against the original path instead of needing to update the pkgmap.
                    if "raw"+os.sep in relfn_trans:
                        pkgs = pkgmap.get(relfn_trans.replace("raw"+os.sep, ""), "")
                    else:
                        pkgs = pkgmap.get(relfn_trans, "")
                    pkgsblk = pkgmap_blacklist.get(relfn_trans, "")
                    if not pkgs:
                        print_debug("WARNING: Could not find which pkg this path belongs, file not patched: {} (original path {})".format(relfn_trans, relfn))
                        if not ignoremissing:
                            raise Exception("Exiting due to warning")
                        continue
                    if pkgsblk:
                        print_debug("WARNING: File blacklisted, file not patched: {})".format(relfn_trans))
                        if not ignoremissing:
                            raise Exception("Exiting due to warning")
                        continue
                    for pkg in pkgs:
                        #only patch if the file does not exist in the blacklist pkgmap.
                        if pkg not in pkgsblk:
                            #default
                            pkgname = pkg
                            #fast_patch forces the pkg name to be the first PKG for all file, if the 
                            #gamename isn't Recom or Movies as those are only in a single PKG anyway.
                            if fastpatch:
                                if gamename != "Recom" or gamename != "Movies":
                                    pkgname = gamename + "_first"
                            #"remastered" and "raw" paths are always already in their own folders 
                            #so no need to add the folder name to the newfn path.
                            if "remastered"+os.sep in relfn_trans or "raw"+os.sep in relfn_trans:
                                newfn = os.path.join("khbuild", pkgname, relfn_trans)
                            else:
                                newfn = os.path.join("khbuild", pkgname, "original", relfn_trans)
                            new_basedir = os.path.dirname(newfn)
                            if not os.path.exists(new_basedir):
                                os.makedirs(new_basedir)
                            shutil.copy(fn, newfn)
        other_patches = []
        if extra_patches_dir and os.path.exists(extra_patches_dir):
            other_patches = [os.path.join(extra_patches_dir,p) for p in os.listdir(extra_patches_dir) if p.endswith(".kh2pcpatch")] #TODO double check extension
        zipped_files = {}
        for patch in sorted(other_patches):
            # Read the patch in as a zip, or extract it out to some temp dir
            # copy the files in based on the pkgmap
            input_zip=ZipFile(patch)
            for name in input_zip.namelist():
                zipped_files[name] = input_zip.read(name)
        for fn in zipped_files:
            if len(zipped_files[fn]) == 0:
                continue
            #default
            fastfn = fn
            #extract all kh2pcpatch files to the first PKG if fast_patch is used.
            if fastpatch:
                if gamename != "Recom" or gamename != "Movies":
                    if "/original/" in fn:
                        fastfn = gamename+"_first/original/"+fn.split("/original/")[1]
                    elif "/remastered/" in fn:
                        fastfn = gamename+"_first/remastered/"+fn.split("/remastered/")[1]
                    elif "/raw/" in fn:
                        fastfn = gamename+"_first/raw/"+fn.split("/raw/")[1]
            newfn = os.path.join("khbuild", fastfn)
            # mods manager needs to take priority
            if not os.path.exists(newfn): 
                new_basedir = os.path.dirname(newfn)
                if not os.path.exists(new_basedir):
                    os.makedirs(new_basedir)
                open(newfn, "wb").write(zipped_files[fn])
        for pkg in os.listdir("khbuild"):
            pkgfile = os.path.join(PKGDIR, pkg+".pkg")
            modfolder = os.path.join("khbuild", pkg)
            if not os.path.exists(os.path.join(modfolder, "remastered")):
                os.makedirs(os.path.join(modfolder, "remastered"))
            if not os.path.exists(os.path.join(modfolder, "original")):
                os.makedirs(os.path.join(modfolder, "original"))
            if not os.path.exists(os.path.join(modfolder, "raw")):
                os.makedirs(os.path.join(modfolder, "raw"))
            if os.path.exists("pkgoutput"):
                shutil.rmtree("pkgoutput")
            print_debug("Patching: {}".format(pkg))
            args = [IDXPATH, "hed", "patch", pkgfile, modfolder, "-o", "pkgoutput"]
            #print_debug(IDXPATH, "hed", "patch", '"{}"'.format(pkgfile), '"modfolder"', "-o", '"{}"'.format("pkgoutput"))
            try:
                print_debug(args, verbose=False)
                output = subprocess.check_output(args, stderr=subprocess.STDOUT).decode('utf-8').replace("\n", "")
                print_debug(output, verbose=True)
            except subprocess.CalledProcessError as err:
                output = err.output
                print(output.decode('utf-8'))
                raise Exception("Patch failed")
            shutil.copy(os.path.join("pkgoutput", pkg+".pkg"), os.path.join(PKGDIR, pkg+".pkg"))
            shutil.copy(os.path.join("pkgoutput", pkg+".hed"), os.path.join(PKGDIR, pkg+".hed"))
        if not keepkhbuild:
            shutil.rmtree("khbuild")
    print_debug("All done! Took {}s".format(round(time.time()-starttime, 2)) + " | Mode: " + mode)

if __name__ == "__main__":
    import sys
    if "cmd" in sys.argv:
        main()
    else:
        main_ui()
