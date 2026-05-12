(function() {
    function applyFilter(catType) {
        var map = {
            'board':   '\u0648\u06cc\u0698\u06af\u06cc\u200c\u0647\u0627\u06cc \u0628\u0631\u062f \u062f\u0648\u0631\u0628\u06cc\u0646',
            'lens':    '\u0648\u06cc\u0698\u06af\u06cc\u200c\u0647\u0627\u06cc \u0644\u0646\u0632 \u062f\u0648\u0631\u0628\u06cc\u0646',
            'modem':   '\u0648\u06cc\u0698\u06af\u06cc\u200c\u0647\u0627\u06cc \u0645\u062a\u0639\u0644\u0642\u0627\u062a',
            'housing': '\u0648\u06cc\u0698\u06af\u06cc\u200c\u0647\u0627\u06cc \u0628\u062f\u0646\u0647 \u062f\u0648\u0631\u0628\u06cc\u0646',
        };
        var specTitles = Object.values(map);

        document.querySelectorAll('fieldset').forEach(function(fs) {
            var h2 = fs.querySelector('h2');
            if (!h2) return;
            var title = h2.textContent.trim();
            if (specTitles.indexOf(title) === -1) return;

            if (!catType || !map[catType]) {
                fs.style.display = 'none';
            } else if (map[catType] === title) {
                fs.style.display = '';
                fs.classList.remove('collapsed');
            } else {
                fs.style.display = 'none';
            }
        });
    }

    function getCatType(catId) {
        if (!catId) { applyFilter(''); return; }
        fetch('/api/catalog/categories/')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var cats = Array.isArray(data) ? data : (data.results || []);
                var cat = cats.find(function(c) { return String(c.id) === String(catId); });
                applyFilter(cat ? cat.category_type : '');
            })
            .catch(function() { applyFilter(''); });
    }

    document.addEventListener('DOMContentLoaded', function() {
        var catField = document.getElementById('id_category');
        if (!catField) return;
        getCatType(catField.value);
        catField.addEventListener('change', function() {
            getCatType(this.value);
        });
    });
})();
