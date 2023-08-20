{
  description = "Spectroscopy lock application using RedPitaya";

  # Updating this triggers a lot of rebuilds, since scipy has many dependents,
  # prepare yourself before updating.
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.gitignore = {
    url = "github:hercules-ci/gitignore.nix";
    # Use the same nixpkgs
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.pyrp3 = {
    url = "github:linien-org/pyrp3";
    flake = false;
  };
  inputs.mdio-tool = {
    url = "github:linien-org/mdio-tool";
    flake = false;
  };
  # Ideally the rest of these python deps should be part of nixpkgs. See also:
  # https://github.com/alexdelorenzo/app_paths/issues/1
  inputs.app-paths = {
    url = "github:alexdelorenzo/app_paths";
    flake = false;
  };
  inputs.unpackable = {
    url = "github:alexdelorenzo/unpackable";
    flake = false;
  };
  inputs.aiopath = {
    url = "github:alexdelorenzo/aiopath";
    flake = false;
  };

  outputs = { self
    , nixpkgs
    , flake-utils
    , gitignore
    , pyrp3
    , app-paths
    , unpackable
    , aiopath
    , mdio-tool
  }:
  flake-utils.lib.eachDefaultSystem (system:
    let
      # Credit @kranzes <3: https://github.com/NixOS/nix/issues/8163#issuecomment-1517774089
      flakeDate2human = flakeInput: builtins.concatStringsSep "-" (builtins.match "(.{4})(.{2})(.{2}).*" flakeInput.lastModifiedDate);
      # Generate a `python` interpreter, with some python packages overriden
      # and added - we merge the pythonOverrides of scipy-fork as well. We use
      # lib.composeExtensions as instructed here:
      # https://github.com/NixOS/nixpkgs/issues/44426
      lockFile = builtins.fromJSON (builtins.readFile ./flake.lock);
      pkgs = import nixpkgs {
        inherit system;
        overlays = [
          (self: super: {
            mdio-tool = self.callPackage ./mdio-tool.nix {
              src = self.fetchFromGitHub {
                inherit (lockFile.nodes.mdio-tool.original)
                  owner
                  repo
                ;
                sha256 = lockFile.nodes.mdio-tool.locked.narHash;
                rev = lockFile.nodes.mdio-tool.locked.rev;
              };
              version = flakeDate2human mdio-tool;
            };
          })
        ];
      };
      inherit (pkgs) lib;
      pythonDevEnv = (python.withPackages(ps: builtins.attrValues {
        inherit (ps)
        app-paths
        click
        cma
        matplotlib
        migen
        misoc
        myhdl
        numpy
        paramiko
        plumbum
        pylpsd
        pyqt5
        pyqtgraph
        pyrp3
        pytestCheckHook
        pytest-plt
        rpyc
        superqt
        scipy # From our fork
        # For text editor
        jedi-language-server
        debugpy
        # For testing installations
        setuptools
        setuptools-scm
        ;
      })).overrideAttrs (old: {
        meta = old.meta // {
          description = "Linien Python development environment";
        };
      });
      inherit (gitignore.lib) gitignoreFilterWith;
      get-src = subdirectory: lib.cleanSourceWith {
        filter = gitignoreFilterWith {
          basePath = ./.;
          extraRules = ''
            flake*
          '';
        };
        src = "${self}/${subdirectory}";
      };
      get-github-src = pname: pkgs.fetchFromGitHub {
        inherit (lockFile.nodes.${pname}.original)
          owner
          repo
        ;
        sha256 = lockFile.nodes.${pname}.locked.narHash;
        rev = lockFile.nodes.${pname}.locked.rev;
      };
      linienBuildArgs = {
        version = (builtins.fromJSON (builtins.readFile ./version-info.json)).latest;
      };
      pythonOverrides = lib.composeExtensions
        # Empty override, may be useful in the future
        (selfPython: superPython: {})
        (selfPython: superPython: {
          linien-gui = superPython.python.pkgs.callPackage ./linien-gui/pkg.nix (linienBuildArgs // {
            src = get-src "linien-gui";
            inherit (selfPython)
              linien-client
              pyqtgraph
              app-paths
            ;
          });
          linien-client = superPython.python.pkgs.callPackage ./linien-client/pkg.nix (linienBuildArgs // {
            src = get-src "linien-client";
            inherit (selfPython)
              linien-common
            ;
          });
          linien-common = superPython.python.pkgs.callPackage ./linien-common/pkg.nix (linienBuildArgs // {
            src = get-src "linien-common";
          });
          linien-server = superPython.python.pkgs.callPackage ./linien-server/pkg.nix (linienBuildArgs // {
            src = get-src "linien-server";
            inherit (selfPython)
              linien-common
              pylpsd
              pyrp3
            ;
            inherit (selfPython.python.pkgs.pkgs) mdio-tool;
          });
          pyrp3 = superPython.python.pkgs.callPackage ./pyrp3 {
            src = get-github-src "pyrp3";
            version = flakeDate2human pyrp3;
          };
          app-paths = superPython.python.pkgs.callPackage ./app-paths {
            src = get-github-src "app-paths";
            version = flakeDate2human app-paths;
            inherit (selfPython)
              unpackable
              aiopath
            ;
          };
          unpackable = superPython.python.pkgs.callPackage ./unpackable {
            src = get-github-src "unpackable";
            version = flakeDate2human unpackable;
          };
          aiopath = superPython.python.pkgs.callPackage ./aiopath {
            src = get-github-src "aiopath";
            version = flakeDate2human aiopath;
          };
        })
      ;
      python = (pkgs.python3.override {
        packageOverrides = pythonOverrides;
      }).overrideAttrs(old: {
        meta = old.meta // {
          description = "Python interpreter with .pkgs set including linien";
        };
      });
      python-armv7l-hf-multiplatform = (pkgs.pkgsCross.armv7l-hf-multiplatform.python3.override {
        packageOverrides = pythonOverrides;
      }).overrideAttrs(old: {
        meta = old.meta // {
          description = "Python interpreter (cross compiled) with .pkgs set including linien";
        };
      });
      buildDeb = {pkg, targetArch, pkgName ? pkg.name}: pkgs.stdenv.mkDerivation {
        name = "${pkg.name}.deb";
        buildInputs = [
          pkgs.dpkg
        ];
        unpackPhase = "true";
        buildPhase = ''
          export HOME=$PWD
          mkdir -p pkgtree/nix/store/
          for item in "$(cat ${pkgs.referencesByPopularity pkg})"; do
            cp -r $item pkgtree/nix/store/
          done

          mkdir -p pkgtree/bin
          cp -r ${pkg}/bin/* pkgtree/bin/
          mkdir -p pkgtree/lib
          cp -r ${pkg}/lib/systemd pkgtree/lib/

          chmod -R a+rwx pkgtree/nix
          chmod -R a+rwx pkgtree/bin
          mkdir pkgtree/DEBIAN
          cat << EOF > pkgtree/DEBIAN/control
          Package: ${pkgName}
          Version: ${pkg.version}
          Maintainer: "github.com/bleykauf"
        ''
        # TODO: Ideally we would parse `pkgs.stdenv.gcc.arch` or a similar
        # attribute and use this argument such that dpkg-deb will be
        # satisfied with our name of the platform.
        + ''
          Architecture: ${targetArch}
          Description: ${pkg.meta.description}
          EOF
        '';
        installPhase = ''
          dpkg-deb -b pkgtree
          mv pkgtree.deb $out
        '';
        meta = {
          description = "Debian package of ${pkg.name} compiled for architecture ${targetArch}";
        };
      };
    in {
      devShells = {
        default = pkgs.mkShell {
          nativeBuildInputs = [
            pythonDevEnv
            # To inspect deb packages we build, using:
            #
            #    dpkg --contents $(nix build --print-out-paths -L .\#linien-server-deb-armv7l-hf-multiplatform)`
            pkgs.dpkg
            # To manage linien.bin
            pkgs.git-lfs
          ];
        };
      };
      packages = {
        # Put it here so it'll be easy to run commands such as:
        #
        #    nix why-depends --all --derivation .\#python.pkgs.linien-gui .\#nixpkgs-python.pkgs.scipy
        #
        nixpkgs-python = pkgs.python3;
        inherit pythonDevEnv;
        inherit (pkgs) mdio-tool;
        mdio-tool-static = pkgs.pkgsCross.armv7l-hf-multiplatform.pkgsStatic.mdio-tool;
        # The server is built for debian only, so we don't inherit it here
        inherit (python.pkgs)
          linien-common
          linien-client
          linien-gui
        ;
        inherit
          python
          python-armv7l-hf-multiplatform
        ;
        linien-server-deb-armv7l-hf-multiplatform = buildDeb {
          pkg = python-armv7l-hf-multiplatform.pkgs.linien-server;
          targetArch = "armhf";
          pkgName = "linien-server";
        };
      };
    }
  );
}
