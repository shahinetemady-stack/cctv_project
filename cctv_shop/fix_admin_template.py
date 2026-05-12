"""
python fix_admin_template.py
"""
import os, subprocess, sys

# template برای change_form با JS داخلی
tpl_dir = os.path.join('templates','admin','catalog','product')
os.makedirs(tpl_dir, exist_ok=True)

with open(os.path.join(tpl_dir,'change_form.html'), 'w', encoding='utf-8') as f:
    f.write('''{% extends "admin/change_form.html" %}
{% block admin_change_form_document_ready %}
{{ block.super }}
<script>
(function() {
    var map = {
        'board':   'ویژگی\u200cهای برد دوربین',
        'lens':    'ویژگی\u200cهای لنز دوربین',
        'modem':   'ویژگی\u200cهای متعلقات',
        'housing': 'ویژگی\u200cهای بدنه دوربین',
    };
    var specTitles = Object.values(map);

    function applyFilter(catType) {
        document.querySelectorAll('fieldset').forEach(function(fs) {
            var h2 = fs.querySelector('h2');
            if (!h2) return;
            var title = h2.textContent.trim();
            if (specTitles.indexOf(title) === -1) return;
            if (!catType) {
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
            });
    }

    var catField = document.getElementById('id_category');
    if (catField) {
        getCatType(catField.value);
        catField.addEventListener('change', function() { getCatType(this.value); });
    }
})();
</script>
{% endblock %}
''')
print("OK - change_form.html")

r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'], capture_output=True, text=True)
print("OK - check" if r.returncode == 0 else r.stderr[-200:])
print("\nتمام! python manage.py runserver")
