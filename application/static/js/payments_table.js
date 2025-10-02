$(document).ready(function() {
    // Initialize DataTable
    let table = $('#payments-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/payments/get_payments',
            type: 'GET',
            data: function(d) {
                // Send the selected status filter to Flask
                d.search = $('#status-filter-input').val() || '';
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
                data: 'status',
                render: function(data) {
                    if (!data) return '-';
                    switch(data.toLowerCase()) {
                        case 'synced':
                            return '<span class="text-green-600 bg-green-100 px-2 py-1 rounded-md text-sm font-medium">Synced</span>';
                        case 'unsynced':
                            return '<span class="text-yellow-600 bg-yellow-100 px-2 py-1 rounded-md text-sm font-medium">Unsynced</span>';
                        case 'failed':
                            return '<span class="text-red-600 bg-red-100 px-2 py-1 rounded-md text-sm font-medium">Failed</span>';
                        default:
                            return '<span class="badge badge-secondary">' + data + '</span>';
                    }
                }
            },
            { data: 'pushed_by', defaultContent: '-' },
            { data: 'pushed_date', defaultContent: '-' }
        ],
        order: [[0, 'desc']]
    });

    // Hidden input to store selected status
    if ($('#status-filter-input').length === 0) {
        $("body").append('<input type="hidden" id="status-filter-input">');
    }

    // Status button click → set active & reload table
    $(".status-filter").on("click", function() {
        // Remove active ring from all buttons
        $(".status-filter").removeClass("ring-2 ring-blue-500");

        // Add active ring to clicked button
        $(this).addClass("ring-2 ring-blue-500");

        // Update hidden input and reload table
        $("#status-filter-input").val($(this).data("status") || '');
        table.ajax.reload();
    });
});
