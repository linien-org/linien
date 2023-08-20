{ lib
, buildPythonPackage
, version
, src
, click
, cma
, pylpsd
, pyrp3
, rpyc
, linien-common
, requests
, mdio-tool
, python
}:

buildPythonPackage {
  pname = "linien-server";
  inherit version;

  inherit src;

  propagatedBuildInputs = [
    click
    cma
    pylpsd
    pyrp3
    rpyc
    linien-common
    requests
  ];
  postInstall = ''
    # Not needed in declarative Nix installations
    rm $out/bin/linien_install_requirements.sh
    rm $out/${python.sitePackages}/linien_server/linien_install_requirements.sh
    mkdir -p $out/lib/systemd/system
    mv $out/${python.sitePackages}/linien_server/linien.service $out/lib/systemd/system/linien.service
    substituteInPlace $out/lib/systemd/system/linien.service \
      --replace /usr/bin/mdio-tool ${mdio-tool}/bin/mdio-tool \
      --replace /usr/bin/linien-server $out/bin/linien-server
  '';

  pythonImportsCheck = [
    "linien_server"
  ];

  meta = with lib; {
    description = "Server components of the Linien spectroscopy lock application";
    homepage = "https://github.com/linien-org/linien";
    license = licenses.gpl3;
  };
}
