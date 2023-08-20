{ lib
, src
, version
, buildPythonPackage
}:

buildPythonPackage {
  pname = "unpackable";
  inherit version;

  inherit src;

  pythonImportsCheck = [
    "unpackable"
  ];
  # See also https://github.com/alexdelorenzo/unpackable/commit/d685ae9be0040d6020cdda6de9225e6d3c210ef6
  preConfigure = ''
    sed -i /varname/d requirements.txt
  '';

  meta = with lib; {
    description = "A module that lets you use Python's destructuring assignment to unpack an object's attributes.";
    homepage = "https://github.com/alexdelorenzo/unpackable";
    license = licenses.lgpl3Plus;
  };
}
