from nicegui import ui

button = (
    ui.button('Testing').style(''' position: fixed;left: 30px;top: 30px;width: 60px;
    height:60px;z-index: 9999;cursor: grab; ''').props('id=floating-btn')
)

ui.add_body_html("""
<script>
window.addEventListener('load', () => {

http://localhost:8000
    if (!btn) {
        console.log('Button not found');
        return;
    }

    let dragging = false;
    let offsetX = 0;
    let offsetY = 0;

    btn.addEventListener('mousedown', (e) => {
        dragging = true;

        const rect = btn.getBoundingClientRect();

        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;

        btn.style.cursor = 'grabbing';

        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (!dragging) return;

        btn.style.left = `${e.clientX - offsetX}px`;
        btn.style.top = `${e.clientY - offsetY}px`;
    });

    window.addEventListener('mouseup', () => {
        dragging = false;
        btn.style.cursor = 'grab';
    });

});
</script>
""")

ui.run(native=True)