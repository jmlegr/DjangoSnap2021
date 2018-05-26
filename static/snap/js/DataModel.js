class Data {
  constructor() {
    this.dataObject = {
      contenu: undefined,
      targetId: "id"
    };
    var that = this
    var _getData = function(i) {
      if (that.dataObject.targetId == undefined) return that.dataObject.contenu[i];
      if (typeof that.dataObject.targetId === "string")
        return that.dataObject.contenu.find(d => d[that.dataObject.targetId] == i)
      if (typeof that.dataObject.targetId === "function")
        return that.dataObject.contenu.find(d => that.dataObject.targetId(d) == i)
    }
    var _findData = function(f, all = false) {
      return all ? that.dataObject.contenu.filter(f) : that.dataObject.contenu.find(f)
    }


    this.id = function(value) {
      if (!arguments.length) {
        return this.dataObject.targetId
      }
      this.dataObject.targetId = value;
      return this;
    }



    this.find = function(value) {
      if (arguments.length && typeof value === "function") {
        return _findData(value);
      }
      return undefined;
    }
    this.findAll = function(value) {
      if (arguments.length && typeof value === "function") {
        return _findData(value, true);
      }
      return undefined;
    }

    this.data = function(value) {
      if (!arguments.length) return this.dataObject.contenu;
      this.dataObject.contenu = value;
      if (arguments.length > 1) {
        this.dataObject.targetId = arguments[1];
      }
    }
    this.get = function(value) {
      if (!arguments.length) {
        return this.dataObject.targetId
      }
      return _getData(value);
    }
  }
}
