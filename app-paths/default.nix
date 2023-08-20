{ lib
, src
, version
, buildPythonPackage
, setuptools
, unpackable
, asyncstdlib
, appdirs
, aiopath
, strenum
}:

buildPythonPackage {
  pname = "app-paths";
  inherit version;

  inherit src;

  pythonImportsCheck = [
    "app_paths"
  ];

  propagatedBuildInputs = [
    unpackable
    asyncstdlib
    appdirs
    aiopath
    strenum
  ];

  meta = with lib; {
    description = "Like appdirs, but with pathlib, path creation and async support";
    homepage = "https://github.com/alexdelorenzo/app_paths";
    license = licenses.lgpl3Plus;
  };
}
