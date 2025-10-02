$(document).ready(function() {
    let table = $('#payments-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/payments/get_payments',
            type: 'GET',
            data: function(d) {
                // Send the status filter value to Flask
                d.search = $('#status-filter').val(); // send as `search` so backend mapping works
            }
        },
        columns: [
            { data: 'id' },
            { data: 'reg_no' },
            { data: 'reference_number', defaultContent: '-' },
            { data: 'amount', defaultContent: 0 },
            { data: 'transaction_id', defaultContent: '-' },
            { data: 'payment_date', defaultContent: '-' },
            { data: 'status', defaultContent: '-' },
            { data: 'pushed_by', defaultContent: '-' },
            { data: 'pushed_date', defaultContent: '-' }
        ],
        order: [[0, 'desc']]
    });

    // Reload table when filter changes
    $('#status-filter').on('change', function() {
        table.ajax.reload();
    });
});
