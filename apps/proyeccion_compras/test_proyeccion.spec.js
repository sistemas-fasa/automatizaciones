const { test, expect } = require('@playwright/test');
const path = require('path');

const HTML_PATH = 'file://' + path.resolve(__dirname, 'outputs', 'proyeccion.html');

test.describe('Proyeccion HTML', () => {
  test('should match VFP totals for provider 0004 snapshot', async ({ page }) => {
    await page.goto(HTML_PATH);
    await page.selectOption('#filterProv', '0004');
    const subtotal = page.locator('tr.subtotal');
    await expect(subtotal).toContainText('$2.114.652,667');
    await expect(subtotal).toContainText('$2.788.377,424');
  });

  test('should render all sections without console errors', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));

    await page.goto(HTML_PATH, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // 1. Stat cards (7)
    expect(await page.locator('.stat-card').count()).toBe(7);

    // 2. Charts (5)
    for (const id of ['#chartPedido', '#chartCostoPedido', '#chartStockProv', '#chartTopArticulos', '#chartTopCosto']) {
      await expect(page.locator(id)).toBeVisible();
    }

    // 3. Table rows (>0)
    const dataRows = page.locator('table tbody tr:not(.prov-group):not(.subtotal)');
    expect(await dataRows.count()).toBeGreaterThan(0);
    expect(await dataRows.first().locator('td').count()).toBe(16);

    // 4. Tooltip on Dias Cob. header
    const diasCobHeader = page.locator('th:has-text("Dias Cob.")');
    await expect(diasCobHeader).toBeVisible();
    expect(await diasCobHeader.getAttribute('title')).toBeTruthy();
    const headerRow = diasCobHeader.locator('xpath=..');
    const headerBackgroundBeforeHover = await headerRow.evaluate(
      element => getComputedStyle(element).backgroundColor
    );
    await diasCobHeader.hover();
    await expect.poll(() => headerRow.evaluate(
      element => getComputedStyle(element).backgroundColor
    )).toBe(headerBackgroundBeforeHover);

    // 5. No JS errors
    expect(consoleErrors).toEqual([]);
  });

  test('should add Resto to every Top chart without losing totals', async ({ page }) => {
    await page.goto(HTML_PATH, { waitUntil: 'networkidle' });

    const result = await page.evaluate(() => {
      const chartSpecs = [
        ['chartPedido', DATA.reduce((sum, p) => sum + p.total_pedido_real, 0)],
        ['chartCostoPedido', DATA.reduce((sum, p) => sum + p.total_costo_pedido_real, 0)],
        ['chartStockProv', DATA.reduce((sum, p) => sum + p.total_stock, 0)],
        ['chartTopArticulos', DATA.flatMap(p => p.articulos).reduce((sum, a) => sum + a.pedido_real, 0)],
        ['chartTopCosto', DATA.flatMap(p => p.articulos).reduce((sum, a) => sum + a.pedido_real * a.costo_unitario, 0)],
      ];

      return {
        helperType: typeof topNConResto,
        charts: chartSpecs.map(([id, expectedTotal]) => {
          const chart = Chart.getChart(document.getElementById(id));
          return {
            id,
            labels: chart.data.labels,
            values: chart.data.datasets[0].data,
            expectedTotal,
          };
        }),
      };
    });

    expect(result.helperType).toBe('function');
    for (const chart of result.charts) {
      expect(chart.labels).toContain('Resto');
      const displayedTotal = chart.values.reduce((sum, value) => sum + value, 0);
      expect(Math.abs(displayedTotal - chart.expectedTotal)).toBeLessThanOrEqual(0.25);
    }

    const withoutExcludedItems = await page.evaluate(() =>
      topNConResto([{ value: 3 }, { value: 2 }], item => item.value, 2)
    );
    expect(withoutExcludedItems).toHaveLength(2);
    expect(withoutExcludedItems.some(entry => entry.label === 'Resto')).toBe(false);
  });

  test('should render the industrial premium theme without sacrificing table readability', async ({ page }) => {
    await page.goto(HTML_PATH, { waitUntil: 'networkidle' });

    const theme = await page.evaluate(() => {
      const root = document.documentElement;
      const styles = getComputedStyle(root);
      const bodyStyles = getComputedStyle(document.body);
      const chartCardStyles = getComputedStyle(document.querySelector('.chart-card'));
      const dataCellStyles = getComputedStyle(document.querySelector('.table-wrap'));
      const chart = Chart.getChart(document.getElementById('chartPedido'));
      return {
        theme: root.dataset.theme,
        surfaceDark: styles.getPropertyValue('--surface-dark').trim(),
        accentElectric: styles.getPropertyValue('--accent-electric').trim(),
        bodyBackground: bodyStyles.backgroundColor,
        chartBackground: chartCardStyles.backgroundColor,
        tableCellBackground: dataCellStyles.backgroundColor,
        tooltipBackground: chart.options.plugins.tooltip.backgroundColor,
      };
    });

    expect(theme.theme).toBe('industrial');
    expect(theme.surfaceDark).toBeTruthy();
    expect(theme.accentElectric).toBeTruthy();
    expect(theme.bodyBackground).not.toBe('rgb(248, 249, 250)');
    expect(theme.chartBackground).toBe('rgb(21, 29, 40)');
    expect(theme.tableCellBackground).toBe('rgb(255, 255, 255)');
    expect(theme.tooltipBackground).toBe('rgba(7, 12, 20, 0.96)');
  });
});
