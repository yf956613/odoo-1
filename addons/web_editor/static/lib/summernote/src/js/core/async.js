define('summernote/core/async', function () {
  /**
   * @class core.async
   *
   * Async functions which returns `Promise`
   *
   * @singleton
   * @alternateClassName async
   */
  var async = (function () {
    /**
     * @method readFileAsDataURL
     *
     * read contents of file as representing URL
     *
     * @param {File} file
     * @return {Promise} - then: sDataUrl
     */
    var readFileAsDataURL = function (file) {
      return new Promise(function (resolve, reject) {
        $.extend(new FileReader(), {
          onload: function (e) {
            var sDataURL = e.target.result;
            resolve(sDataURL);
          },
          onerror: function () {
            reject(this);
          }
        }).readAsDataURL(file);
      }).promise();
    };

    /**
     * @method createImage
     *
     * create `<image>` from url string
     *
     * @param {String} sUrl
     * @param {String} filename
     * @return {Promise} - then: $image
     */
    var createImage = function (sUrl, filename) {
      return new Promise(function (resolve, reject) {
        var $img = $('<img>');

        $img.one('load', function () {
          $img.off('error abort');
          resolve($img);
        }).one('error abort', function () {
          $img.off('load').detach();
          reject($img);
        }).css({
          display: 'none'
        }).appendTo(document.body).attr({
          'src': sUrl,
          'data-filename': filename
        });
      }).promise();
    };

    return {
      readFileAsDataURL: readFileAsDataURL,
      createImage: createImage
    };
  })();

  return async;
});
