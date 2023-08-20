{ lib
, buildPythonPackage
, version
, src
, numpy
, scipy
, importlib-metadata
, rpyc
, appdirs
}:

buildPythonPackage {
  pname = "linien-common";
  inherit version;

  inherit src;

  propagatedBuildInputs = [
    numpy
    scipy
    importlib-metadata
    rpyc
    appdirs
  ];
  # https://github.com/linien-org/pyrp3/pull/10#pullrequestreview-1585887668
  # From some reason pythonRelaxDepsHook doesn't work here
  preConfigure = ''
    substituteInPlace setup.py \
      --replace "rpyc>=4.0,<5.0" rpyc
  '';

  pythonImportsCheck = [
    "linien_common"
  ];

  meta = with lib; {
    description = "Shared components of the Linien spectroscopy lock application";
    homepage = "https://github.com/linien-org/linien";
    license = licenses.gpl3;
  };
}
