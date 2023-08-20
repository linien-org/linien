{ lib
, src
, version
, buildPythonPackage
, anyio
, aiofile
}:

buildPythonPackage {
  pname = "aiopath";
  inherit version;

  inherit src;

  propagatedBuildInputs = [
    anyio
    aiofile
  ];
  # Tests require a module that is deprecated, and is not packaged in Nixpkgs,
  # named: asynctempfile. URL: https://github.com/alemigo/asynctempfile .
  # Ideally upstream would adopt less obscure dependencies.
  doCheck = false;

  pythonImportsCheck = [
    "aiopath"
  ];

  meta = with lib; {
    description = "A complete implementation of Python's pathlib that's compatible with asyncio, trio, and the async/await syntax";
    homepage = "https://github.com/alexdelorenzo/aiopath";
    license = licenses.lgpl3Plus;
  };
}
