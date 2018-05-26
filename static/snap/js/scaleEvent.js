function scaleEvent(options = {}) {
/// échelle permettant de passer d'une liste temporelle d'évènements
/// (temps sous forme d'entiers)
/// à une représentation sur un range
/// si le temps t est l'évènement n° n,
/// il correspond à la valeur n
/// si un temps est entre deux évènements,
/// il correspond à une valeur entre les deux évènements,
/// proportionnelle au temps séparant ces deux évènements
  var base; // = d3.scaleLinear()
  var _times = []
  var rounded = options.rounded || true;
  var toTicks, invert;

  function me(value) {
    toTicks = function(d) {
      if (!_times.length || d < _times[0]) return undefined
      var r = _times.indexOf(d);
      if (r != -1)
        return r;
      //c'est un ticks correspondant à un évènement autre que SPR
      for (var i in _times) {
        if (_times[i] > d) {
          return (i - 1 + (d - _times[i - 1]) / (_times[i] - _times[i - 1]))
        }
      }
      return _times.length;
    }
    invert = function(d) {
      var v = base.invert(d)
      if (Number.isInteger(v) && v >= 0 && v <= _times.length) {
        return _times[v];
      }
      // ce n'est pas un temps correspondant à un tick,
      // il est entre 2
      var i1 = Math.floor(v),
        i = Math.ceil(v);
      return rounded ? Math.round(_times[i1] + (v - i1) * (_times[i] - _times[i1])) : _times[i1] + (v - i1) * (_times[i] - _times[i1])

    }
    return base(toTicks(value));
  }
  me.invert = function(value) {
  //entrée: position sur le svg [0,width]
  //sortie: temps arrondi si rounded=true
    return invert(value)
  }
  me.toTicks = function(value) {
  //entrée: temps
  //sortie: valeur sur le domaine [0,_times.length]
    return toTicks(value);
  }
  me.invertTicks=function (value) {
  //entrée: position sur le svg [0,width]
  //sortie: valeur sur le domaine [0,_times.length]
   return toTicks(invert(value));
  }
  me.domain = function(value) {
  //domain entré sous forme d'un tableau de temps
  //rendu sous la forme [0,_times.length]
  //avec _times[0]=première valeur du temps etc...
    if (!arguments.length) return _times;
    _times = value;
    base.domain([0, _times.length])
    return me;
  }
  me.range = function(value) {
    if (!arguments.length) return base.range;
    base.range(value);
    return me;
  }
  base=origScale?origScale:d3.scaleLinear();
  return me;
}