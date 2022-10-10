{
  description = "Spectroscopy lock application using RedPitaya";

  # See https://github.com/NixOS/nixpkgs/pull/195144
  inputs.nixpkgs.url = "github:doronbehar/nixpkgs/pkg/linien";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self
    , nixpkgs
    , flake-utils
  }:
  flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs {
        inherit system;
      };
    in rec {
      devShells = {
        default = pkgs.mkShell {
          nativeBuildInputs = [
            (pkgs.python3.withPackages(ps: with ps; [
              appdirs
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
              scipy
              superqt
              # For text editor
              jedi-language-server
              debugpy
            ]))
          ];
        };
      };
    }
  );
}
