{ lib
, stdenv
, src
, version
, cmake
}:

stdenv.mkDerivation {
  pname = "mdio-tool";
  inherit version src;

  nativeBuildInputs = [
    cmake
  ];

  meta = with lib; {
    description = "A tool to read and write MII registers from ethernet physicals under linux";
    homepage = "https://github.com/linien-org/mdio-tool";
    license = licenses.gpl2Plus;
    platforms = platforms.linux;
  };
}
