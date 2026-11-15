/* Sito di vendita di Impaginatore: poche cose, e la pagina funziona anche senza.
   1. Copia dei comandi d'installazione negli appunti, con annuncio per i lettori di schermo.
   2. Pagina di ringraziamento: mostra solo il blocco che corrisponde a «?per=lista» o «?per=acquisto».
   3. Rete di sicurezza del prezzo di lancio: se la data scritta in <html data-fine-lancio> è passata e nessuno
      ha ancora rieseguito «sito.py configura», mostra il prezzo di listino al posto di quello di lancio e
      nasconde le frasi che parlano del lancio.
   4. Il menu delle pagine strette si chiude quando scegli una voce.
   Nessuna richiesta di rete, nessun cookie, nessuna memoria locale. */
(function () {
  "use strict";
  var doc = document.documentElement;
  var it = (doc.getAttribute("lang") || "it").indexOf("it") === 0;

  // 1. copia
  function annuncia(bottone, testo) {
    var id = bottone.getAttribute("aria-describedby");
    var zona = id && document.getElementById(id);
    if (zona) { zona.textContent = testo; window.setTimeout(function () { zona.textContent = ""; }, 4000); }
  }
  function copiaVecchioStile(testo) {
    var area = document.createElement("textarea");
    area.value = testo; area.setAttribute("readonly", ""); area.style.position = "absolute"; area.style.left = "-9999px";
    document.body.appendChild(area); area.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(area);
    return ok;
  }
  Array.prototype.forEach.call(document.querySelectorAll("button[data-copia]"), function (b) {
    b.hidden = false;
    b.addEventListener("click", function () {
      var sorgente = document.getElementById(b.getAttribute("data-copia"));
      if (!sorgente) return;
      var testo = sorgente.textContent.trim();
      var fatto = function () { annuncia(b, it ? "Comando copiato negli appunti." : "Command copied to the clipboard."); };
      var fallito = function () { annuncia(b, it ? "Copia non riuscita: seleziona il comando e copialo a mano." : "Copy failed: select the command and copy it by hand."); };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(testo).then(fatto, function () { (copiaVecchioStile(testo) ? fatto : fallito)(); });
      else (copiaVecchioStile(testo) ? fatto : fallito)();
    });
  });

  // 2. ringraziamento
  var per = (location.search.match(/[?&]per=([a-z]+)/) || [])[1];
  var blocchi = document.querySelectorAll("[data-per]");
  if (per && blocchi.length && document.querySelector('[data-per="' + per + '"]')) {
    Array.prototype.forEach.call(blocchi, function (el) { el.hidden = el.getAttribute("data-per") !== per; });
  }

  // 3. fine del lancio
  var fine = doc.getAttribute("data-fine-lancio");
  if (fine && /^\d{4}-\d{2}-\d{2}$/.test(fine)) {
    var oggi = new Date(), p = fine.split("-");
    var ultimo = new Date(+p[0], +p[1] - 1, +p[2], 23, 59, 59);
    if (oggi > ultimo) {
      Array.prototype.forEach.call(document.querySelectorAll("[data-listino]"), function (el) { el.textContent = el.getAttribute("data-listino"); });
      Array.prototype.forEach.call(document.querySelectorAll('[data-se~="lancio"]'), function (el) { el.hidden = true; });
      Array.prototype.forEach.call(document.querySelectorAll('[data-se-non~="lancio"]'), function (el) {
        if (el.getAttribute("data-se-non").trim() === "lancio" && !el.hasAttribute("data-se")) el.hidden = false;
      });
    }
  }

  // 4. menu
  Array.prototype.forEach.call(document.querySelectorAll("details.menu a"), function (a) {
    a.addEventListener("click", function () { var d = a.closest("details"); if (d) d.open = false; });
  });
})();
