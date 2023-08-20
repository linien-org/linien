{ lib
, src
, version
, buildPythonPackage
, setuptools
, importlib-metadata
, myhdl
, rpyc
, cached-property
, numpy
}:

buildPythonPackage {
  pname = "pyrp3";
  inherit version;
  format = "pyproject";

  inherit src;

  pythonImportsCheck = [
    "pyrp3"
    "pyrp3.board"
  ];
  # https://github.com/linien-org/pyrp3/pull/10#pullrequestreview-1585887668
  # From some reason pythonRelaxDepsHook doesn't work here
  preConfigure = ''
    substituteInPlace setup.py \
      --replace "rpyc>=4.0,<5.0" rpyc
  '';

  nativeBuildInputs = [
    setuptools
  ];

  propagatedBuildInputs = [
    importlib-metadata
    myhdl
    rpyc
    cached-property
    numpy
  ];

  meta = with lib; {
    description = "Python 3 port of PyRedPitaya library providing access to Red Pitaya registers";
    homepage = "https://github.com/linien-org/pyrp3";
    license = licenses.bsd3;
    platforms = platforms.linux;
  };
}
