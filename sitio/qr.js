// El código QR del billete, dibujado en el navegador y sin dependencias.
//
// Es el mismo algoritmo que `backend/scripts/generar_qr.py`, paso por paso:
// modo byte, nivel de corrección Q, versiones 1 a 6. Está duplicado a propósito
// y no servido por la API: el código de recogida ya está en el teléfono, y
// pedirle al servidor una imagen de un dato que la pantalla ya tiene sería una
// petición más justo cuando la red del auditorio está peor. Lo que ata las dos
// copias es `backend/tests/test_qr.py`, que comprueba la matriz de este
// archivo contra la de Python con los mismos textos.
//
// ### Qué se codifica, y por qué no solo el código
//
// `pideutb:<pedido>:<código>`. El mostrador necesita las dos cosas: a qué
// pedido se refiere, para saber a cuál pedirle la entrega, y el código, que es
// lo que el servidor compara. Con el código a secas, el panel tendría que
// probarlo contra cada pedido listo, que es exactamente la enumeración que
// ESC-04 prohíbe. El prefijo es lo que deja al panel distinguir un QR nuestro
// de cualquier otro que le pongan delante de la cámara.
//
// El número de pedido ya es secuencial y visible, así que el QR no revela nada
// que la pantalla no enseñe. El código sigue siendo la llave.
//
// ### Por qué Q y no L
//
// Se escanea de la pantalla de un teléfono, a veces con brillo bajo y reflejos.
// Q recupera el 25 % de los módulos. Para un texto de 18 a 22 caracteres sale
// la versión 2, 25 × 25 módulos, que a 160 px de lado da más de 6 px por
// módulo: lo que cualquier cámara enfoca a un palmo.

const QR = (() => {
  // Cada fila: [codewords de corrección por bloque, [[bloques, codewords de datos], ...]].
  const BLOQUES_Q = {
    1: [13, [[1, 13]]],
    2: [22, [[1, 22]]],
    3: [18, [[2, 17]]],
    4: [26, [[2, 24]]],
    5: [18, [[2, 15], [2, 16]]],
    6: [24, [[4, 19]]],
  };

  const ALINEACION = { 1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34] };

  const NIVEL_Q = 0b11;

  const datosDe = (grupos) => grupos.reduce((suma, [bloques, cw]) => suma + bloques * cw, 0);

  // --- GF(256) ---------------------------------------------------------------

  const EXP = new Array(512).fill(0);
  const LOG = new Array(256).fill(0);
  (() => {
    let x = 1;
    for (let i = 0; i < 255; i++) {
      EXP[i] = x;
      LOG[x] = i;
      x <<= 1;
      if (x & 0x100) x ^= 0x11d;
    }
    for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  })();

  const multiplicar = (a, b) => (a === 0 || b === 0 ? 0 : EXP[LOG[a] + LOG[b]]);

  function polinomioGenerador(grado) {
    let g = [1];
    for (let i = 0; i < grado; i++) {
      const siguiente = new Array(g.length + 1).fill(0);
      g.forEach((coeficiente, j) => {
        siguiente[j] ^= coeficiente;
        siguiente[j + 1] ^= multiplicar(coeficiente, EXP[i]);
      });
      g = siguiente;
    }
    return g;
  }

  function corregir(datos, cuantos) {
    const generador = polinomioGenerador(cuantos);
    const resto = datos.concat(new Array(cuantos).fill(0));
    for (let i = 0; i < datos.length; i++) {
      const factor = resto[i];
      if (factor) {
        generador.forEach((coeficiente, j) => {
          resto[i + j] ^= multiplicar(coeficiente, factor);
        });
      }
    }
    return resto.slice(datos.length);
  }

  // --- De texto a codewords -------------------------------------------------

  function versionPara(bytes) {
    for (const version of Object.keys(BLOQUES_Q).map(Number).sort((a, b) => a - b)) {
      const datosCw = datosDe(BLOQUES_Q[version][1]);
      if (bytes.length <= Math.floor((datosCw * 8 - 12) / 8)) return version;
    }
    throw new Error(`${bytes.length} caracteres no caben en un QR de nivel Q hasta la versión 6`);
  }

  /** Modo byte, con su terminador y su relleno, ya partido en codewords. */
  function aCodewords(bytes, datosCw) {
    const bits = [];
    const meter = (valor, cuantos) => {
      for (let i = cuantos - 1; i >= 0; i--) bits.push((valor >> i) & 1);
    };

    meter(0b0100, 4);
    meter(bytes.length, 8);
    for (const byte of bytes) meter(byte, 8);

    meter(0, Math.min(4, datosCw * 8 - bits.length));
    while (bits.length % 8) bits.push(0);

    const relleno = [0xec, 0x11];
    let vuelta = 0;
    while (bits.length < datosCw * 8) {
      meter(relleno[vuelta % 2], 8);
      vuelta += 1;
    }

    const codewords = [];
    for (let i = 0; i < bits.length; i += 8) {
      codewords.push(Number.parseInt(bits.slice(i, i + 8).join(""), 2));
    }
    return codewords;
  }

  /** Reparto en bloques con su corrección, y el entrelazado final. */
  function entrelazar(codewords, grupos, ecPorBloque) {
    const bloquesDatos = [];
    const bloquesEc = [];
    let desde = 0;
    for (const [cuantosBloques, cwPorBloque] of grupos) {
      for (let b = 0; b < cuantosBloques; b++) {
        const trozo = codewords.slice(desde, desde + cwPorBloque);
        desde += cwPorBloque;
        bloquesDatos.push(trozo);
        bloquesEc.push(corregir(trozo, ecPorBloque));
      }
    }

    // Un codeword de cada bloque por vuelta: una mancha sobre el código
    // reparte el daño entre bloques en vez de destruir uno entero.
    const salida = [];
    const masLargo = Math.max(...bloquesDatos.map((b) => b.length));
    for (let i = 0; i < masLargo; i++) {
      for (const bloque of bloquesDatos) if (i < bloque.length) salida.push(bloque[i]);
    }
    for (let i = 0; i < ecPorBloque; i++) {
      for (const bloque of bloquesEc) salida.push(bloque[i]);
    }
    return salida;
  }

  function codificar(bytes, version) {
    const [ecPorBloque, grupos] = BLOQUES_Q[version];
    return entrelazar(aCodewords(bytes, datosDe(grupos)), grupos, ecPorBloque);
  }

  // --- De codewords a matriz ------------------------------------------------

  function ponerBuscador(m, reservado, fila, columna) {
    const lado = m.length;
    for (let i = -1; i < 8; i++) {
      for (let j = -1; j < 8; j++) {
        const f = fila + i;
        const c = columna + j;
        if (f < 0 || f >= lado || c < 0 || c >= lado) continue;
        const borde = (i === 0 || i === 6) && j >= 0 && j <= 6;
        const costado = (j === 0 || j === 6) && i >= 0 && i <= 6;
        const centro = i >= 2 && i <= 4 && j >= 2 && j <= 4;
        m[f][c] = borde || costado || centro ? 1 : 0;
        reservado[f][c] = true;
      }
    }
  }

  function ponerAlineacion(m, reservado, version) {
    const lado = m.length;
    const centros = ALINEACION[version];
    const chocaConBuscador = (fila, columna) =>
      (fila === 6 && columna === 6) ||
      (fila === 6 && columna === lado - 7) ||
      (fila === lado - 7 && columna === 6);

    for (const fila of centros) {
      for (const columna of centros) {
        if (chocaConBuscador(fila, columna)) continue;
        for (let i = -2; i <= 2; i++) {
          for (let j = -2; j <= 2; j++) {
            const anillo = Math.max(Math.abs(i), Math.abs(j));
            m[fila + i][columna + j] = anillo === 1 ? 0 : 1;
            reservado[fila + i][columna + j] = true;
          }
        }
      }
    }
  }

  function ponerSincronizacionYFormato(m, reservado) {
    const lado = m.length;
    for (let i = 8; i < lado - 8; i++) {
      const valor = i % 2 === 0 ? 1 : 0;
      if (!reservado[6][i]) { m[6][i] = valor; reservado[6][i] = true; }
      if (!reservado[i][6]) { m[i][6] = valor; reservado[i][6] = true; }
    }

    // El módulo que siempre vale 1.
    m[lado - 8][8] = 1;
    reservado[lado - 8][8] = true;

    // Y el espacio de la cadena de formato, que se rellena al final.
    for (let i = 0; i < 9; i++) {
      reservado[8][i] = true;
      reservado[i][8] = true;
    }
    for (let i = 0; i < 8; i++) {
      reservado[8][lado - 1 - i] = true;
      reservado[lado - 1 - i][8] = true;
    }
  }

  /** La matriz con los patrones fijos puestos, y qué celdas quedan libres. */
  function matrizVacia(version) {
    const lado = 17 + 4 * version;
    const m = Array.from({ length: lado }, () => new Array(lado).fill(null));
    const reservado = Array.from({ length: lado }, () => new Array(lado).fill(false));

    ponerBuscador(m, reservado, 0, 0);
    ponerBuscador(m, reservado, 0, lado - 7);
    ponerBuscador(m, reservado, lado - 7, 0);
    ponerAlineacion(m, reservado, version);
    ponerSincronizacionYFormato(m, reservado);

    return [m, reservado];
  }

  /** Zigzag de dos columnas desde abajo a la derecha. */
  function colocar(m, reservado, codewords) {
    const lado = m.length;
    const bits = [];
    for (const cw of codewords) for (let i = 7; i >= 0; i--) bits.push((cw >> i) & 1);
    let siguiente = 0;

    const escribir = (fila, c) => {
      if (reservado[fila][c]) return;
      m[fila][c] = siguiente < bits.length ? bits[siguiente] : 0;
      siguiente += 1;
    };

    let arriba = true;
    for (let columna = lado - 1; columna > 0; columna -= 2) {
      if (columna === 6) columna -= 1;   // la línea de sincronización no cuenta como columna
      for (let paso = 0; paso < lado; paso++) {
        const fila = arriba ? lado - 1 - paso : paso;
        escribir(fila, columna);
        escribir(fila, columna - 1);
      }
      arriba = !arriba;
    }
  }

  const MASCARAS = [
    (f, c) => (f + c) % 2 === 0,
    (f) => f % 2 === 0,
    (f, c) => c % 3 === 0,
    (f, c) => (f + c) % 3 === 0,
    (f, c) => (Math.floor(f / 2) + Math.floor(c / 3)) % 2 === 0,
    (f, c) => ((f * c) % 2) + ((f * c) % 3) === 0,
    (f, c) => (((f * c) % 2) + ((f * c) % 3)) % 2 === 0,
    (f, c) => (((f + c) % 2) + ((f * c) % 3)) % 2 === 0,
  ];

  // Las cuatro reglas del estándar, que miden lo difícil que será de leer.

  /** 1: rachas de cinco o más del mismo color. */
  function penalizarRachas(lineas) {
    let total = 0;
    for (const linea of lineas) {
      let racha = 0;
      let anterior = null;
      for (const valor of linea) {
        if (valor === anterior) {
          racha += 1;
          continue;
        }
        if (racha >= 5) total += 3 + (racha - 5);
        racha = 1;
        anterior = valor;
      }
      if (racha >= 5) total += 3 + (racha - 5);
    }
    return total;
  }

  /** 2: bloques de 2×2 del mismo color. */
  function penalizarBloques(m) {
    const lado = m.length;
    let total = 0;
    for (let f = 0; f < lado - 1; f++) {
      for (let c = 0; c < lado - 1; c++) {
        const v = m[f][c];
        if (v === m[f][c + 1] && v === m[f + 1][c] && v === m[f + 1][c + 1]) total += 3;
      }
    }
    return total;
  }

  /** 3: el patrón que se confunde con un buscador. */
  const PATRONES_DE_BUSCADOR = new Set(["10111010000", "00001011101"]);

  function penalizarBuscadoresFalsos(lineas) {
    let total = 0;
    for (const linea of lineas) {
      const texto = linea.join("");
      for (let i = 0; i + 11 <= texto.length; i++) {
        if (PATRONES_DE_BUSCADOR.has(texto.slice(i, i + 11))) total += 40;
      }
    }
    return total;
  }

  /** 4: desequilibrio entre claros y oscuros. */
  function penalizarDesequilibrio(m) {
    const lado = m.length;
    const oscuros = m.reduce((suma, fila) => suma + fila.reduce((s, v) => s + v, 0), 0);
    const porcentaje = Math.floor((oscuros * 100) / (lado * lado));
    return 10 * Math.min(
      Math.floor(Math.abs(porcentaje - 50) / 5),
      Math.floor(Math.abs(porcentaje - 50 + 4) / 5)
    );
  }

  function penalizacion(m) {
    const columnas = m[0].map((_, c) => m.map((fila) => fila[c]));
    const lineas = m.concat(columnas);
    return (
      penalizarRachas(lineas) +
      penalizarBloques(m) +
      penalizarBuscadoresFalsos(lineas) +
      penalizarDesequilibrio(m)
    );
  }

  /** BCH(15,5) de los cinco bits de formato, con su XOR final. */
  function formato(mascara) {
    const datos = (NIVEL_Q << 3) | mascara;
    let resto = datos << 10;
    for (let i = 14; i > 9; i--) {
      if (resto & (1 << i)) resto ^= 0b10100110111 << (i - 10);
    }
    return ((datos << 10) | resto) ^ 0b101010000010010;
  }

  function escribirFormato(m, mascara) {
    const lado = m.length;
    const valor = formato(mascara);
    const bits = [];
    for (let i = 14; i >= 0; i--) bits.push((valor >> i) & 1);

    const posiciones = [[8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
      [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8]];
    posiciones.forEach(([f, c], i) => { m[f][c] = bits[i]; });

    for (let i = 0; i < 7; i++) m[lado - 1 - i][8] = bits[i];
    for (let i = 0; i < 8; i++) m[8][lado - 8 + i] = bits[7 + i];
  }

  /** El texto, hecho matriz de ceros y unos, ya enmascarada. */
  function construir(texto) {
    const bytes = Array.from(new TextEncoder().encode(texto));
    const version = versionPara(bytes);
    const codewords = codificar(bytes, version);

    const [m, reservado] = matrizVacia(version);
    colocar(m, reservado, codewords);

    // Se prueban las ocho máscaras y gana la de menor penalización. No es
    // opcional: el estándar lo exige, y una máscara mala produce un código que
    // algunos lectores no enfocan.
    let mejor = null;
    let mejorPuntos = Infinity;
    MASCARAS.forEach((mascara, indice) => {
      const intento = m.map((fila, f) =>
        fila.map((celda, c) => (!reservado[f][c] && mascara(f, c) ? celda ^ 1 : celda))
      );
      escribirFormato(intento, indice);
      const puntos = penalizacion(intento);
      if (puntos < mejorPuntos) {
        mejor = intento;
        mejorPuntos = puntos;
      }
    });
    return mejor;
  }

  /**
   * La matriz como `<svg>`, con la zona tranquila de cuatro módulos dentro.
   *
   * Se construye con la API del DOM y no concatenando texto: lo único variable
   * son números, pero es la misma regla que vale para todo el sitio — nada
   * entra por `innerHTML`.
   */
  function aSvg(matriz, etiqueta) {
    const ns = "http://www.w3.org/2000/svg";
    const lado = matriz.length;
    const margen = 4;
    const total = lado + margen * 2;

    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", `0 0 ${total} ${total}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", etiqueta);
    svg.setAttribute("shape-rendering", "crispEdges");

    const fondo = document.createElementNS(ns, "rect");
    fondo.setAttribute("width", total);
    fondo.setAttribute("height", total);
    fondo.setAttribute("fill", "#ffffff");
    svg.appendChild(fondo);

    // Un rectángulo por racha horizontal de módulos oscuros, no uno por módulo.
    const trazo = [];
    matriz.forEach((fila, f) => {
      let c = 0;
      while (c < lado) {
        if (!fila[c]) {
          c += 1;
          continue;
        }
        const inicio = c;
        while (c < lado && fila[c]) c += 1;
        trazo.push(`M${inicio + margen} ${f + margen}h${c - inicio}v1h-${c - inicio}z`);
      }
    });
    const modulos = document.createElementNS(ns, "path");
    modulos.setAttribute("d", trazo.join(""));
    modulos.setAttribute("fill", "#000000");
    svg.appendChild(modulos);
    return svg;
  }

  return { construir, aSvg };
})();
