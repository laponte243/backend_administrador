<script>
  Highcharts.chart('container', {
      chart: {
          type: 'column'
      },
      title: {
          text: 'Titanic Survivors by Ticket Class'
      },
      xAxis: {
          categories: [
            {% for entry in dataset %}'{{ entry.ticket_class }} Class'{% if not forloop.last %}, {% endif %}{% endfor %}
          ]
      },
      series: [{
          name: 'Survived',
          data: [
            {% for entry in dataset %}{{ entry.survived_count }}{% if not forloop.last %}, {% endif %}{% endfor %}
          ],
          color: 'green'
      }, {
          name: 'Not survived',
          data: [
            {% for entry in dataset %}{{ entry.not_survived_count }}{% if not forloop.last %}, {% endif %}{% endfor %}
          ],
          color: 'red'
      }]
  });
</script>