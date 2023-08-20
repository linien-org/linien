{ lib
, buildPythonPackage
, version
, src
, fabric
, numpy
, typing-extensions
, linien-common
}:

buildPythonPackage {
  pname = "linien-client";
  inherit version;

  inherit src;

  propagatedBuildInputs = [
    fabric
    numpy
    typing-extensions
    linien-common
  ];

  pythonImportsCheck = [
    "linien_client"
  ];

  meta = with lib; {
    description = "Client components of the Linien spectroscopy lock application";
    homepage = "https://github.com/linien-org/linien";
    license = licenses.gpl3;
  };
}
