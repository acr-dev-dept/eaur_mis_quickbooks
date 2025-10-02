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
            {
                data: 'QuickBk_Status',
                render: function(data, type, row) {
                    if (data == 1 && row.qk_id != null) {
                        return '<span class="text-green-600 bg-green-100 px-2 py-1 rounded-md text-sm font-medium">Synced</span>';
                    }
                    if ((data == 2 || data == 3) && row.qk_id == null) {
                        return '<span class="text-red-600 bg-red-100 px-2 py-1 rounded-md text-sm font-medium">Failed</span>';
                    }
                    if (data == null || data == 0 || row.qk_id == null) {
                        return '<span class="text-yellow-600 bg-yellow-100 px-2 py-1 rounded-md text-sm font-medium">Unsynced</span>';
                    }
                    return '-';
                }
            },
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
